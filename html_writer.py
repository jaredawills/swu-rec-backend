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


def replace_text(mapping, text):
    for key, value in mapping.items():
        text = re.sub(key, value, text)
    return text


def write_index():
    logger.info('Writing index')
    index_html = read_file(path('html_pieces/index.html'))
    index_set_section = read_file(path('html_pieces/index_set_section.html'))
    index_set_leader_article = read_file(path('html_pieces/index_set_leader_article.html'))
    sets = db_conn.read('sets')
    cards = db_conn.read('cards')
    set_sections = []
    set_filter = []
    for set in sets.itertuples():
        set_leaders = cards[(cards['set_code']==set.set_code) & (cards['card_type']=='Leader')].sort_values('card_id')
        if set_leaders.shape[0] > 0:
            leader_articles = []
            for leader in set_leaders.itertuples():
                sub_map = {
                    '%card_num': re.sub('_', '-', leader.card_id),
                    '%card_id': leader.card_id,
                    '%lower_title': leader.title.lower(),
                    '%title': leader.title,
                    '%subtitle': leader.subtitle,
                    '%back_art': leader.back_art,
                    '%set_code': leader.set_code
                }
                leader_articles.append(replace_text(sub_map, index_set_leader_article[:]))
            sub_map = {
                '%set_code': set.set_code,
                '%title': set.title,
                '%leader_grid': '\n'.join(leader_articles),
            }
            set_sections.append(replace_text(sub_map, index_set_section[:]))
            set_filter.append(f'<option value=\"{set.set_code}\">{set.title}</option>')
    index_html = re.sub('%set_filter', '\n'.join(set_filter), index_html)
    index_html = re.sub('%set_sections', '\n'.join(set_sections), index_html)
    write_file(path('html/index.html'), index_html)
            

def get_leader_articles(card_grid=[], card_id=None):
    if type(card_grid) == list:
        query = re.sub('%card_id', card_id, read_file('advanced_leader_query.sql'))  
        card_grid = db_conn.query(query)
    leader_card_article = read_file('html_pieces/leader_card_article.html')
    articles = []
    for card in card_grid.itertuples():
        sub_map = {
            '%card_type': card.card_type,
            '%aspects': re.sub(',', ' ', card.aspects if card.aspects else ''),
            '%set_code': card.set_code if card.set_code else '',
            '%copy3': str(round(card.copy3 / card.tot_decks * 100, 2)),
            '%copy2': str(round(card.copy2 / card.tot_decks * 100, 2)),
            '%copy1': str(round(card.copy1 / card.tot_decks * 100, 2)),
            '%front_art': card.front_art,
            '%title': card.title,
            '%subtitle': card.subtitle if card.subtitle else '',
            '%card_num': re.sub('_', '-', card.card_id),
        }
        articles.append(replace_text(sub_map, leader_card_article[:]))
    return '\n'.join(articles)


def write_set_leader_pages(sets, cards, set_code):
    leaders = cards[(cards['set_code']==set_code) & (cards['card_type']=='Leader')].sort_values('card_id')
    leader_html = read_file('html_pieces/leader.html')
    for leader in leaders.itertuples():
        logger.debug(f'Writing {leader.card_id}')
        card_grid_query = re.sub('%card_id', leader.card_id, read_file('advanced_leader_query.sql'))  
        card_grid = db_conn.query(card_grid_query)
        sub_map = {
            '%title': leader.title,
            '%subtitle': leader.subtitle,
            '%set_title': sets[sets['set_code']==set_code]['title'].values[0],
            '%set_code': set_code,
            '%card_num': re.sub('_', '-', leader.card_id),
            '%aspects': re.sub(',', ' ', leader.aspects),
            '%traits': ' '.join([t.title() for t in leader.traits.split(',')]),
            '%front_text': leader.front_text,
            '%back_text': leader.back_text,
            '%front_art': leader.front_art,
            '%back_art': leader.back_art,
            '%set_filters': '\n'.join([f'<option value=\"{set.set_code}\">{set.title}</option>' for set in sets.itertuples() if set.set_code in card_grid['set_code'].drop_duplicates().values]),
            '%card_grid': get_leader_articles(card_grid=card_grid),
            '%decks': str(db_conn.query(f'SELECT COUNT(*) FROM deck_leaders WHERE card_id = \'{leader.card_id}\'').values[0][0])
        }
        write_file(f'html/{leader.set_code}/{leader.card_id}.html', replace_text(sub_map, leader_html[:]))
  
    
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
