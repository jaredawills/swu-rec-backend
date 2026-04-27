# -*- coding: utf-8 -*-
"""
Created on Apr 09, 2026

@author: jared
"""

import db_conn
import requests
import pandas as pd
import json
from loguru import logger
import regex as re
from pathlib import Path

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


Options.page_load_strategy = 'eager'


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
            db_conn.insert_into('cards', columns, rows.values)
            logger.success(f'{rows.shape[0]}x {set_code} cards updated in database')
        else:
            logger.info(f'{set_code} has 0 available cards')
    except Exception as e:
        logger.error(f'Unable to complete {set_code} || {e}')


def download_set_list():
    url = 'https://www.swudb.com/sets'
    logger.debug('Launching Chrome Driver')
    service = Service(executable_path='')
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=options)
    logger.debug(f'Connecting to: {url}')
    driver.get(url)
    timeout = 0
    set_pattern = r'<a href="\/sets\/([^\"]*)" class="swudb-hover-link">([^<]*)<\/a>'
    date_pattern = r'Release Date:<\/span> ([^<]*)<\/p>'
    sets = [] 
    while timeout < 5 and len(sets) < 1:
        time.sleep(2)
        timeout += 1
        html = driver.page_source
        sets = re.findall(set_pattern, html)
        dates = re.findall(date_pattern, html)
        sets = [(s[0], s[1], d) for s, d in zip(sets, dates)]
    logger.debug(f'Found {len(sets)} sets')
    sets = pd.DataFrame(sets, columns=['set_code', 'title', 'release_date'])
    sets['release_date'] = pd.to_datetime(sets['release_date']).dt.strftime('%Y-%m-%d')
    db_conn.write(sets, 'sets')


def generic_bases():
    query = read_file('generic_bases.sql')
    with db_conn.get_conn() as conn:
        conn.execute(query)
        conn.commit()


def overhaul_sets():
    db_conn.clear_table('sets')
    download_set_list()


def overhaul_cards():
    sets = db_conn.read('sets')
    for code in sets['set_code']:
        download_set(code)
    generic_bases()


def scrape_swudb(decks, sortby='top', overlap_threshold=100):
    source = 'swudb'
    url = f'https://www.swudb.com/decks/search?deckSort={sortby}'
    pattern = r'href=\"\/deck\/[A-z]*\"'
    logger.debug('Launching Chrome Driver')
    service = Service(executable_path='')
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=options)
    logger.debug(f'Connecting to: {url}')
    driver.get(url)
    new_decks = pd.DataFrame([], columns=['deck_id', 'source'])
    timeout = 0
    height = -1
    overlap = 0
    last_height = driver.execute_script('return document.body.scrollHeight')
    today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    try:
        while (height != last_height or timeout < 40) and overlap < overlap_threshold:
            overlap = 0
            last_height = height
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(5)
            height = driver.execute_script('return document.body.scrollHeight')
            timeout = timeout + 5 if height == last_height else 0
            html = driver.page_source
            deck_href = pd.Series(re.findall(pattern, html)).drop_duplicates()
            for deck_id in deck_href:
                deck_id = deck_id.split('/')[-1][:-1]
                if deck_id in decks[decks['source']==source]['deck_id'].values:
                    overlap += 1
                else:
                    new_decks = pd.concat([new_decks, pd.DataFrame([[deck_id, source, today]], columns=['deck_id', 'source', 'date_inserted'])]).drop_duplicates()
            logger.debug(f'd:{decks.shape[0] + new_decks.shape[0]} | n:{new_decks.shape[0]} | o:{overlap} | h:{height}px | t:{timeout}s')
        logger.debug('End of page reached')
        decks = pd.concat([decks, new_decks]).drop_duplicates()
    except Exception as e:
        logger.error(f'An Error occured: {e}')
    return decks


def scrape_sw_unlimited_db(decks, timeout_threshold=200, new_limit=500):
    source = 'sw-unlimited-db'
    url = 'https://sw-unlimited-db.com/'
    logger.debug(f'Connecting to {url}')
    sw_unlimited_db_html = requests.get(url).text
    max_pattern = r'<a href="\/decks\/(\d+)"'
    max_id = int(re.search(max_pattern, sw_unlimited_db_html).group(1))
    url += '/decks/'
    if str(decks[decks['source']==source]['deck_id'].max()) == 'nan':
        deck_id = 1500
    else:
        deck_id = decks[decks['source']==source]['deck_id'].astype(int).max()
    timeout = 0
    count = 0
    today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    logger.debug(f'Searching id=({deck_id}, {max_id}]')
    try:
        for new_id in range(deck_id + 1, max_id + 1):
        # while timeout < timeout_threshold and (count < new_limit or new_limit < 0):
            # deck_id += 1 
            response = requests.get(url + str(new_id))
            if response.status_code == 200:
                decks = pd.concat([decks, pd.DataFrame([[new_id, source, today]], columns=['deck_id', 'source', 'date_inserted'])])
                count += 1
                timeout = 0
            else:
                timeout += 1
            logger.debug(f'd:{decks.shape[0]} | n:{count} | id:{new_id} | t:{timeout}')
    except Exception as e:
        logger.error(f'An Exception has occured: {e}')
    return decks


def update_cards():
    conn = db_conn.get_conn()
    sets = pd.read_sql('SELECT * FROM sets WHERE DATE(release_date) >= DATE(\'NOW\', \'-6 months\')', conn)
    conn.close()
    logger.debug(f'Updating {sets.shape[0]} sets')
    for code in sets['set_code']:
        download_set(code)


def overhaul_deck_ids():
    decks = pd.DataFrame([], columns=['deck_id', 'source', 'date_inserted'])
    for sortby in ['top', 'discussed', 'new', 'hot']:
        decks = scrape_swudb(decks, sortby, overlap_threshold=500)
    decks = scrape_sw_unlimited_db(decks)
    decks = decks.drop_duplicates()
    logger.info(f'{decks.shape[0]} total deck_ids')
    if decks.shape[0] > 0:
        db_conn.write(decks, 'decks')
        

def get_new_deck_ids():
    decks = db_conn.read('decks')
    decks = scrape_swudb(decks, sortby='new', overlap_threshold=30) # sortby = 'new' / 'hot' / 'top' / 'discussed'
    # decks = scrape_swudb(decks, sortby='top', overlap_threshold=10000)
    decks = scrape_sw_unlimited_db(decks)
    decks = decks.drop_duplicates()
    logger.info(f'{decks.shape[0]} total deck_ids')
    if decks.shape[0] > 0:
        db_conn.write(decks, 'decks')


def download_swudb(deck_id):
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
                [[deck_id, deck['base']['defaultExpansionAbbreviation'] + '_' + deck['base']['defaultCardNumber'], 1]],
                columns=['deck_id', 'card_id', 'num']
            )
            deck_cards = pd.concat([
                deck_bases,
                pd.DataFrame(
                    [[deck_id, card['card']['defaultExpansionAbbreviation'] + '_' + card['card']['defaultCardNumber'], card['count']] for card in deck['shuffledDeck']],
                    columns=['deck_id', 'card_id', 'num']
                )
            ])
            return deck_leaders, deck_cards
        else:
            raise Exception('TS')
    else:
        raise Exception(response.status_code)
    

def download_sw_unlimited_db(deck_id):
    url = f'https://api.sw-unlimited-db.com/umbraco/api/export/export?deckId={deck_id}&exportId=da7e2602-c2d7-4773-9ce1-9f1eb2b2ae8a'
    response = requests.get(url)
    if response.status_code == 200:
        deck = response.json()
        deck_leaders = pd.DataFrame(
            [[deck_id, deck['leader']['id']]],
            columns=['deck_id', 'card_id']
        )
        deck_bases = pd.DataFrame(
            [[deck_id, deck['base']['id'], 1]],
            columns=['deck_id', 'card_id', 'num']
        )
        deck_cards = pd.concat([
            deck_bases,
            pd.DataFrame(
                [[deck_id, card['id'], card['count']] for card in deck['deck']],
                columns=['deck_id', 'card_id', 'num']
            )
        ])
        return deck_leaders, deck_cards
    else:
        raise Exception(response.status_code)


def download_decks():
    conn = db_conn.get_conn()
    today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    decks = pd.read_sql(f'SELECT * FROM decks WHERE DATE(date_inserted) = DATE(\'{today}\')', conn)
    deck_leaders = pd.read_sql('SELECT * FROM deck_leaders', conn)
    deck_cards = pd.read_sql('SELECT * FROM deck_cards', conn)
    success_count = 0
    skipped_count = 0
    for i, decks_row in enumerate(decks.itertuples()):
        try:
            if decks_row.deck_id not in deck_leaders['deck_id'].values:
                try:
                    if decks_row.source == 'swudb':
                        new_leaders, new_cards = download_swudb(decks_row.deck_id)
                    elif decks_row.source == 'sw-unlimited-db':
                        new_leaders, new_cards = download_sw_unlimited_db(decks_row.deck_id)
                    logger.debug(f'{i}/{decks.shape[0]} SUCCESS {decks_row.deck_id}')
                    deck_leaders = pd.concat([deck_leaders, new_leaders])
                    deck_cards = pd.concat([deck_cards, new_cards])
                except Exception as e:
                    skipped_count += 1
                    logger.debug(f'{i}/{decks.shape[0]} SKIPPED {decks_row.deck_id} ({e})')
            else:
                # logger.debug(f'{i}/{decks.shape[0]} SKIPPED {decks_row.deck_id} (EXISTS)')
                True
        except Exception as e:
            logger.error(f'An Exception has occured {e}')
    deck_leaders = deck_leaders.drop_duplicates()
    deck_cards = deck_cards.drop_duplicates()
    # db_conn.write(decks, 'decks')
    db_conn.write(deck_leaders, 'deck_leaders')
    db_conn.write(deck_cards, 'deck_cards')
    conn.commit()
    conn.close()
    logger.info(f'Skipped: {skipped_count}')
    logger.success(f'New Decks: {success_count}')
    logger.success(f'Total Decks: {deck_leaders.shape[0]}')


if __name__ == '__main__':
    t_0 = time.time()
    # overhaul_sets()
    # update_cards()
    get_new_deck_ids()
    download_decks()
    t_1 = time.time()
    logger.success(f'RUN COMPLETE - {int(t_1 - t_0)}s')

