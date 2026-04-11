# -*- coding: utf-8 -*-
"""
Created on Mon Jun  9 14:35:14 2025

@author: jared
"""

from . import db_conn
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from loguru import logger
import regex as re

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


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
            df['CardID'] = df['Set'] + '-' + df['Number']
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


def scrape_set_list():
    url = 'https://www.swudb.com/sets'
    logger.debug('Downloading Driver')
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=options)
    logger.debug(f'Connecting to: {url}')
    driver.get(url)
    timeout = 0
    a_list = []
    while timeout < 5 and len(a_list) < 1:
        time.sleep(1)
        timeout += 1
        # a_list = driver.find_elements(By.TAG_NAME, 'a')
        a_list = driver.find_elements(By.CSS_SELECTOR, '.swudb-hover-link')
    logger.debug(f'Found {len(a_list)} links')
    a_list = list(link.get_attribute('href') for link in a_list if link.get_attribute('href')) # Remove Duplicates and Blanks through casting List>Set>List
    a_list = [link for link in a_list if 'sets' in link]
    a_list = [link.split('/')[-1] for link in a_list if 'sets' in link and link.split('/')[-1] != 'fullSet']
    logger.success(f'Found {len(a_list)} Sets')
    return a_list


def scrape_swudb(deck_ids_df, sortby='top', overlap_threshold=100):
    existing_ids = set(set(deck_ids_df['deck_ids']))
    new_ids = set()
    url = f'https://www.swudb.com/decks/search?deckSort={sortby}'
    pattern = r'href=\"\/deck\/[A-z]*\"'
    logger.debug('Downloading Driver')
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=options)
    logger.debug(f'Connecting to: {url}')
    driver.get(url)
    timeout = 0
    height = -1
    overlap = 0
    last_height = driver.execute_script('return document.body.scrollHeight')
    try:
        while (height != last_height or timeout < 30) and overlap < overlap_threshold :
            last_height = height
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(5)
            height = driver.execute_script('return document.body.scrollHeight')
            timeout = timeout + 5 if height == last_height else 0
            html = driver.page_source
            deck_href = re.findall(pattern, html)
            new_ids.update({l.split('/')[-1][:-1] for l in deck_href})
            overlap = len(existing_ids) - len(existing_ids - new_ids)
            deck_ids = existing_ids.union(new_ids)
            logger.debug(f'd:{len(deck_ids)} | o:{overlap} | h:{height}px | t:{timeout}s')
        logger.debug('End of page reached')
    except Exception as e:
        logger.error(f'An Error occured: {e}')
    deck_ids = existing_ids.union(new_ids)
    return deck_ids


def scrape_sw_unlimited_db(deck_ids_df, timeout_threshold=200, new_limit=500):
    existing_ids = set(deck_ids_df['deck_ids'])
    new_ids = set()
    url = 'https://sw-unlimited-db.com/decks/'
    previous_max = 1500 if str(deck_ids_df['deck_ids'].max()) == 'nan' else deck_ids_df['deck_ids'].max()
    id = previous_max
    timeout = 0
    try:
        while timeout < timeout_threshold and (len(new_ids) < new_limit or new_limit < 0):
            id += 1
            response = requests.get(url + str(id))
            if response.status_code == 200:
                new_ids.update({id})
                timeout = 0
            else:
                timeout += 1
            logger.debug(f'd:{len(existing_ids) + len(new_ids)} | n:{len(new_ids)} | id:{id} | t:{timeout}')
    except Exception as e:
        logger.error(f'An Exception has occured: {e}')

    deck_ids = existing_ids.union(new_ids)
    return deck_ids


def update_cards_db():
    sets = scrape_set_list()
    for set in sets:
        download_set(set)


def overhaul_deck_ids(source='swudb'):
    deck_ids = pd.DataFrame([], columns=['deck_ids'])
    if source == 'swudb':
        for sortby in ['top', 'discussed', 'new', 'hot']:
            deck_ids = pd.DataFrame(scrape_swudb(deck_ids, sortby, overlap_threshold=1000), columns=['deck_ids'])
    elif source == 'sw_unlimtied_db':
        deck_ids = pd.DataFrame(scrape_sw_unlimited_db(deck_ids, new_limit=-1), columns=['deck_ids'])
    
    logger.info(f'{len(deck_ids)} total deck_ids')
    if len(deck_ids > 0):
        deck_ids.to_csv(f'{source}_deck_ids.csv', index=False)
        

def get_new_deck_ids(source='swudb'):
    deck_ids = pd.DataFrame([], columns=['deck_ids'])
    if source == 'swudb':
        deck_ids = pd.read_csv('swudb_deck_ids.csv')
        deck_ids = pd.DataFrame(scrape_swudb(deck_ids, sortby='new', overlap_threshold=100), columns=['deck_ids'])
    elif source == 'sw_unlimited_db':
        deck_ids = pd.read_csv('sw_unlimited_db_deck_ids.csv')
        deck_ids = pd.DataFrame(scrape_sw_unlimited_db(deck_ids, timeout_threshold=1100, new_limit=1000), columns=['deck_ids'])
    logger.info(f'{len(deck_ids)} total deck_ids')
    if len(deck_ids > 0):
        deck_ids.to_csv(f'{source}_deck_ids.csv', index=False)


if __name__ == '__main__':
    for i in range(10):
        get_new_deck_ids(source='sw_unlimited_db')
    logger.success('RUN COMPLETE')

"""
print('Downloading Existing Data from Database')
sets = pd.DataFrame(
    data = db_conn.get_rows('sets'), 
    columns = db_conn.get_cols('sets')
    )
cards = pd.DataFrame(
    data = db_conn.get_rows('cards'), 
    columns = db_conn.get_cols('cards')
    )
decks = pd.DataFrame(
    data = db_conn.get_rows('decks'), 
    columns = db_conn.get_cols('decks')
    )
cards_in_decks = pd.DataFrame(
    data = db_conn.get_rows('cards_in_decks'), 
    columns = db_conn.get_cols('cards_in_decks')
    )
print('Download Complete\n')


print('Downloading New Sets')
url = 'https://sw-unlimited-db.com'
sets_html = req.get(f'{url}/sets/').text
sets_parse = BeautifulSoup(sets_html, 'html.parser')
set_links = [l for l in sets_parse.find_all('a') 
             if '/sets/' in l['href'] and '/sets/' != l['href']]
links = []
for l in set_links[::2]:
    set_id = l.find('i').getText().upper()
    name = l.find('h2').getText()
    if set_id not in sets['set_id']:
        sets.loc[len(sets)] = [set_id, name, 1]
    links.append(l['href'])
print('Download Complete\n')







print('Uploading New Data to Database')
db_conn.insert_into('sets', sets.columns, sets.values)
db_conn.insert_into('cards', cards.columns, cards.values)
db_conn.insert_into('decks', decks.columns, decks.values)
db_conn.insert_into('cards_in_decks', cards_in_decks.columns, cards_in_decks.values)
print('Uploading Complete')
"""