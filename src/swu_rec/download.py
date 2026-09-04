# -*- coding: utf-8 -*-
"""
Created on Apr 09, 2026

@author: jared
"""

import swu_rec.db as db

import requests
import pandas as pd
import json
from loguru import logger
import re
from pathlib import Path
from importlib.resources import files

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

DATA_DIR = files("swu_rec") / "data"
SQL_DIR = DATA_DIR / "sql"


def read_file(in_file):
    with open(in_file, 'rt', encoding='utf-8') as file:
        return file.read()

def write_file(out_file, text):
    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'wt', encoding='utf-8') as file:
        file.write(text)


def download_set(set_code):
    logger.debug(f'Downloading Set {set_code} to database')
    api_url = f'https://api.swu-db.com/cards/{set_code}'
    set_ = json.loads(requests.get(api_url).text)
    try:
        for card in set_["data"]:
            try: card["Aspects"] = ','.join(x["S"] for x in card["Aspects"])
            except: card["Aspects"] = ''
            logger.debug(card["Aspects"])
            try: card["Traits"] = ','.join(x["S"] for x in card["Traits"])
            except: card["Traits"] = ''
            logger.debug(card["Traits"])
        df = pd.DataFrame(set_['data'])
        if df.shape[1] > 0:
            columns = ['card_id',
                    'set_code', 
                    'num', 
                    'title', 
                    'subtitle', 
                    'card_type', 
                    'aspects',
                    'traits',
                    'arenas',
                    'cost',
                    'power',
                    'hp',
                    'front_text',
                    'front_art',
                    'epic_action',
                    'double_sided',
                    'back_text',
                    'back_art',
                    'rarity',
                    'is_unique',
                    'keywords',
                    'artist',
                    'variant_type'
                    ]
            df['CardID'] = df['Set'] + '_' + df['Number'].astype(str).str.zfill(3)
            for col in ['EpicAction', 'BackText', 'BackArt']:
                if col not in df.columns:
                    df[col] = [None] * df.shape[0]
            rows = df[['CardID',
                    'Set',
                    'Number',
                    'Name',
                    'Subtitle',
                    'Type',
                    'Aspects',
                    'Traits',
                    'Arenas',
                    'Cost',
                    'Power',
                    'HP',
                    'FrontText',
                    'FrontArt',
                    'EpicAction',
                    'DoubleSided',
                    'BackText',
                    'BackArt',
                    'Rarity',
                    'Unique',
                    'Keywords',
                    'Artist',
                    'VariantType'
                    ]]
            rows = rows[rows['VariantType']=='Normal']
            logger.debug(f'Found {rows.shape[0]} cards')
            db.insert_into('cards', columns, rows.values)
            logger.success(f'{rows.shape[0]}x {set_code} cards updated in database')
        else:
            logger.info(f'{set_code} has 0 available cards')
    except KeyError as e:
        logger.error(f'Unable to complete {set_code} || API Error')
    except Exception as e:
        logger.error(f'Unable to complete {set_code} || {e}')

def download_set_list():
    url = "https://swudb.com/api/card/getAllSets"
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f'Could not get Sets list. Response: <{response.status_code}>')
    else:
        sets = pd.DataFrame(response.json())[['expansionAbbreviation', 'expansionName', 'releaseDate']]
        sets = sets.rename(columns={
            'expansionAbbreviation': 'set_code',
            'expansionName': 'title',
            'releaseDate': 'release_date'
        })
        sets['release_date'] = pd.to_datetime(sets['release_date']).dt.strftime('%Y-%m-%d')
        db.write(sets, 'sets')


def generic_bases():
    query = read_file(SQL_DIR / 'generic_bases.sql')
    with db.get_conn() as conn:
        conn.execute(query)
        conn.commit()


def overhaul_sets():
    db.clear_table('sets')
    download_set_list()


def overhaul_cards():
    sets = db.read('sets')
    for code in sets['set_code']:
        download_set(code)
    generic_bases()


def update_cards():
    conn = db.get_conn()
    sets = pd.read_sql('SELECT * FROM sets WHERE DATE(release_date) >= DATE(\'NOW\', \'-6 months\')', conn)
    conn.close()
    logger.debug(f'Updating {sets.shape[0]} from the last 6 months')
    for code in sets['set_code']:
        download_set(code)

        
def get_new_decks():
    new_swudb_ct = scrape_swudb()
    new_sw_unlimited_db_ct = scrape_sw_unlimited_db()
    db.drop_duplicates()
    logger.info(f'Found {new_swudb_ct}x new decks from SWUDB')
    logger.info(f'Found {new_sw_unlimited_db_ct}x new decks from sw-unlimited-db')
    total_ids_ct = db.query("SELECT COUNT(1) FROM decks").iloc[0,0]
    logger.info(f'Total Decks: {total_ids_ct}')


def scrape_swudb(decks=None):
    logger.info("Looking for new SWUDB decks")
    decks = decks or db.read("decks")
    url = "https://swudb.com/api/decks/getNewDecks"
    deck_ids = set(decks["deck_id"])
    new_deck_ids = set([])
    count = 0
    static = 0
    while static <= 10 and count <= 6000:
        prev = count
        response = requests.post(
            url = url,
            headers = {"content-type": "application/json"},
            data = json.dumps({"skip": count, "sortby": "new"})
        )
        for deck_id in {deck["deckId"] for deck in response.json()["decks"]}:
            if deck_id not in deck_ids.union(new_deck_ids):
                status_code = download_swudb(deck_id)
                if status_code == 200:
                    count += 1
                    logger.debug(f"Found | id: {deck_id:<13}\tc: {str(count):<5}\tsource: swudb")
                    new_deck_ids = new_deck_ids.union({deck_id})
        if prev == count:
            static += 1
    logger.success(f"Complete! Found {count} new decks from swudb")
    return count

def download_swudb(deck_id):
    today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    url = f'https://swudb.com/api/deck/{deck_id}'
    response = requests.get(url)
    if response.status_code == 200:
        deck = response.json()
        if deck['secondLeader'] == None:
            deck_leaders = pd.DataFrame(
                [[deck_id, deck['leader']['defaultExpansionAbbreviation'] + '_' + deck['leader']['defaultCardNumber']]],
                columns=['deck_id', 'card_id']
            )
            deck_bases = pd.DataFrame(
                [[deck_id, deck['base']['defaultExpansionAbbreviation'] + '_' + deck['base']['defaultCardNumber'], 1, 0]],
                columns=['deck_id', 'card_id', 'num', 'is_sideboard']
            )
            deck_cards = pd.DataFrame(
                [[deck_id, card['card']['defaultExpansionAbbreviation'] + '_' + card['card']['defaultCardNumber'], card['count'], 0] for card in deck['shuffledDeck'] if card['count'] > 0],
                columns=['deck_id', 'card_id', 'num', 'is_sideboard']
            )
            deck_cards = pd.concat([
                df for df in [
                    deck_bases,
                    deck_cards
                ] if df.shape[0] > 0
            ])
            decks = pd.DataFrame(
                [[deck_id, "swudb", today, deck["publishDate"][:10]]],
                columns = ["deck_id", "source", "date_inserted", "date_created"]
            )
            db.append(decks, "decks")
            time.sleep(0.15)
            h_decks = decks[["deck_id", "source", "date_inserted"]]
            db.append(h_decks, "historic_decks")
            time.sleep(0.15)
            db.append(deck_leaders, "deck_leaders")
            time.sleep(0.15)
            db.append(deck_cards, "deck_cards")
            time.sleep(0.15)
            return 200
    return 404


def scrape_sw_unlimited_db(decks=None):
    decks = decks or db.read("decks")
    url = 'https://sw-unlimited-db.com/decks/'
    response = requests.get(url)
    new_max_id = max([int(x) for x in re.findall(r"\"/decks/(\d+)\"", response.text)])
    max_id = db.query("SELECT MAX(CAST(deck_id AS INT)) FROM decks WHERE source = 'sw-unlimited-db'").iloc[0,0] or 1600
    logger.info(f"Looking for sw-unlimited-db decks between {max_id} and {new_max_id}")
    new_deck_ids = set([])
    count = 0
    for deck_id in range(max_id, new_max_id + 1):
        status_code = download_sw_unlimited_db(deck_id)
        if status_code == 200:
            count += 1
            logger.debug(f"Found | id: {deck_id:<13}\tc: {str(count):<5}\tsource: sw-unlimited-db")
            new_deck_ids = new_deck_ids.union({f"{deck_id}"})
    logger.success(f"Complete! Found {count} new decks from sw-unlimited-db")
    return count

def download_sw_unlimited_db(deck_id):
    today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    url = f'https://api.sw-unlimited-db.com/umbraco/api/export/export?deckId={deck_id}&exportId=da7e2602-c2d7-4773-9ce1-9f1eb2b2ae8a'
    response = requests.get(url)
    if response.status_code == 200:
        deck = response.json()
        deck_leaders = pd.DataFrame(
            [[deck_id, deck['leader']['id']]],
            columns=['deck_id', 'card_id']
        )
        deck_bases = pd.DataFrame(
            [[deck_id, deck['base']['id'], 1, 0]],
            columns=['deck_id', 'card_id', 'num', 'is_sideboard']
        )
        deck_cards = pd.DataFrame(
            [[deck_id, card['id'], card['count']] for card in deck['deck']],
            columns=['deck_id', 'card_id', 'num']
        )
        deck_cards = pd.concat([
            df for df in [
                deck_bases,
                deck_cards,
            ] if not isinstance(df, tuple)
        ])
        response = requests.get(
            f"https://api.sw-unlimited-db.com/api/decks/get?id={deck_id}",
            headers = {"content-type": "application/json"}
            )
        created_date = response.json()["updatedDate"][:10]
        decks = pd.DataFrame(
            [[deck_id, "sw-unlimited-db", today, created_date]]
            , columns=["deck_id", "source", "date_inserted", "date_created"]
        )
        db.append(decks, "decks")
        time.sleep(0.15)
        h_decks = decks[["deck_id", "source", "date_inserted"]]
        db.append(h_decks, "historic_decks")
        time.sleep(0.15)
        db.append(deck_leaders, "deck_leaders")
        time.sleep(0.15)
        db.append(deck_cards, "deck_cards")
        time.sleep(0.15)
        return 200
    return 404


def sync_historic():
    historic_decks = db.read("historic_decks")
    decks = db.read("decks")
    deck_ids = [deck.deck_id for deck in decks.itertuples()]
    for historic_deck in historic_decks.itertuples():
        if historic_deck.deck_id not in deck_ids:
            logger.debug(f"Searching: {historic_deck.deck_id}")
            if historic_deck.source == "swudb": download_swudb(historic_deck.deck_id)
            elif historic_deck.source == "sw_unlimited_db": download_sw_unlimited_db(historic_deck.deck_id)
        else:
            logger.debug(f"Skipping: {historic_deck.deck_id}")



if __name__ == '__main__':
    t_0 = time.time()
    download_set("HMW")
    # overhaul_sets()
    # update_cards()
    # get_new_deck_ids()
    # download_decks()
    t_1 = time.time()
    logger.success(f'RUN COMPLETE - {int(t_1 - t_0)}s')

