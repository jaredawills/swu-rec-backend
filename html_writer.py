# -*- coding: utf-8 -*-
"""
Created on Apr 09, 2026

@author: jared
"""

import db_conn
import pandas as pd
import time
import regex as re
from pathlib import Path

from loguru import logger


def read_file(in_file):
    with open(in_file, 'rt', encoding='utf-8') as file:
        return file.read()
    
def write_file(out_file, text):
    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'wt', encoding='utf-8') as file:
        file.write(text)


def write_index():
    logger.info('Writing index')
    index_html = read_file('html_pieces/index.html')
    index_set_section = read_file('html_pieces/index_set_section.html')
    index_set_leader_article = read_file('html_pieces/index_set_leader_article.html')

    sets = db_conn.read('sets')
    cards = db_conn.read('cards')

    set_sections = []
    set_filter = []
    for set in sets.itertuples():
        set_leaders = cards[(cards['set_code']==set.set_code) & (cards['card_type']=='Leader')].sort_values('card_id')
        if set_leaders.shape[0] > 0:
            leader_articles = []
            for leader in set_leaders.itertuples():
                t = index_set_leader_article[:]
                t = re.sub('%card_num', re.sub('_', '-', leader.card_id), t)
                t = re.sub('%card_id', leader.card_id, t)
                t = re.sub('%lower_title', leader.title.lower(), t)
                t = re.sub('%title', leader.title, t)
                t = re.sub('%subtitle', leader.subtitle, t)
                t = re.sub('%back_art', leader.back_art, t)
                t = re.sub('%set_code', leader.set_code, t)
                leader_articles.append(t)
            t = index_set_section[:]
            t = re.sub('%set_code', set.set_code, t)
            t = re.sub('%title', set.title, t)
            t = re.sub('%leader_grid', '\n'.join(leader_articles), t)
            set_filter.append(f'<option value=\"{set.set_code}\">{set.title}</option>')
            set_sections.append(t)
    index_html = re.sub('%set_filter', '\n'.join(set_filter), index_html)
    index_html = re.sub('%set_sections', '\n'.join(set_sections), index_html)
    write_file('html\\index.html', index_html)
            

def get_leader_articles(card_id):
    query = re.sub('%card_id', card_id, read_file('leader_query.sql'))  
    results = db_conn.query(query)
    leader_card_article = read_file('html_pieces/leader_card_article.html')

    articles = []
    for card in results.itertuples():
        t = leader_card_article[:]
        t = re.sub('%card_type', card.card_type, t)
        aspects = card.aspects if card.aspects else ''
        t = re.sub('%aspects', re.sub(',', ' ', aspects), t)
        t = re.sub('%set_code', card.set_code, t)
        t = re.sub('%copy3', str(round(card.copy3 / card.num_decks * 100, 2)), t)
        t = re.sub('%copy2', str(round(card.copy2 / card.num_decks * 100, 2)), t)
        t = re.sub('%copy1', str(round(card.copy1 / card.num_decks * 100, 2)), t)
        t = re.sub('%front_art', card.front_art, t)
        t = re.sub('%title', card.title, t)
        subtitle = card.subtitle if card.subtitle else ''
        t = re.sub('%subtitle', subtitle, t)
        t = re.sub('%card_num', re.sub('_', '-', card.card_id), t)
        articles.append(t)
    return '\n'.join(articles)


def write_set_leader_pages(sets, cards, set_code):
    set_filters = [f'<option value=\"{set.set_code}\">{set.title}</option>' 
                    for set in sets.itertuples()
                    if cards[cards['set_code']==set.set_code].shape[0] > 0]
    leaders = cards[(cards['set_code']==set_code) & (cards['card_type']=='Leader')].sort_values('card_id')
    leader_html = read_file('html_pieces/leader.html')
    for leader in leaders.itertuples():
        logger.debug(f'Writing {leader.card_id}')
        t = leader_html[:]
        t = re.sub('%title', leader.title, t)
        set_title = sets[sets['set_code']==set_code]['title'].values[0]
        t = re.sub('%set_title', str(set_title), t)
        t = re.sub('%set_code', leader.set_code, t)
        t = re.sub('%subtitle', leader.subtitle, t)
        t = re.sub('%card_num', re.sub('_', '-', leader.card_id), t)
        t = re.sub('%aspects', re.sub(',', ' ', leader.aspects), t)
        t = re.sub('%traits', ' '.join([t.title() for t in leader.traits.split(',')]), t)
        t = re.sub('%front_text', leader.front_text, t)
        t = re.sub('%back_text', leader.back_text, t)
        t = re.sub('%front_art', leader.front_art, t)
        t = re.sub('%back_art', leader.back_art, t)
        t = re.sub('%set_filters', '\n'.join(set_filters), t)
        t = re.sub('%card_grid', get_leader_articles(leader.card_id), t)
        deck_count = db_conn.query(f'SELECT COUNT(*) FROM deck_leaders WHERE card_id = \'{leader.card_id}\'').values[0][0]
        t = re.sub('%decks', str(deck_count), t)
        write_file(f'html/{leader.set_code}/{leader.card_id}.html', t)
        
    
    
def write_leader_pages():
    sets = db_conn.read('sets')
    cards = db_conn.read('cards')
    for set in sets.itertuples():
        set_leaders = cards[(cards['set_code']==set.set_code) & (cards['card_type']=='Leader')].sort_values('card_id')
        if set_leaders.shape[0] > 0:
            logger.info(f'Writing HTML for {set.title} ({set.set_code})')
            write_set_leader_pages(sets, cards, set.set_code)



if __name__ == '__main__':
    t_0 = time.time()
    write_index()
    # write_set_leader_pages(db_conn.read('sets'), db_conn.read('cards'), 'LAW')
    write_leader_pages()
    t_1 = time.time()
    logger.success(f'RUN COMPLETE - {int(t_1 - t_0)}s')
