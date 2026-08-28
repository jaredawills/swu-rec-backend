# -*- coding: utf-8 -*-
"""
Created on Apr 09, 2026

@author: jared
"""

import swu_rec.db as db
import pandas as pd
import time
import re
from pathlib import Path
from importlib.resources import files
from datetime import date

from loguru import logger

HTML = files("swu_rec.data") / "html"
HTML_PIECES = files("swu_rec.data") / "html_pieces"
SQL = files("swu_rec.data") / "sql"

def read_file(in_file):
    in_file = Path(in_file) if type(in_file) == str else in_file
    with open(in_file, 'rt', encoding='utf-8') as file:
        return file.read()

def write_file(out_file, text):
    out_file = Path(out_file) if type(out_file) == str else out_file
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'wt', encoding='utf-8') as file:
        file.write(text)

def replace_text(mapping, text):
    for key, value in mapping.items():
        # logger.debug(key)
        # logger.debug(value)
        text = re.sub(key, value, text)
    return text


def write_index(refresh_time=None):
    refresh_time = refresh_time if refresh_time else time.time()
    logger.info('Writing index')
    index_html = read_file(HTML_PIECES / "index.html")
    index_set_section = read_file(HTML_PIECES / "index_set_section.html")
    index_set_leader_article = read_file(HTML_PIECES / "index_set_leader_article.html")
    sets = db.read('sets')
    cards = db.read('cards')
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
    sub_map = {
        '%set_filter': '\n'.join(set_filter),
        '%set_sections': '\n'.join(set_sections),
        '%time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(refresh_time))
    }
    write_file(HTML / "index.html", replace_text(sub_map, index_html[:]))
            

def get_leader_articles(card_grid=[], card_id=None):
    if type(card_grid) == list:
        query = re.sub('%card_id', card_id, read_file(SQL / "advanced_leader_query.sql"))  
        card_grid = db.query(query)
    leader_card_article = read_file(HTML_PIECES / "leader_card_article.html")
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


def write_set_leader_pages(sets, cards, set_code, refresh_time=None):
    refresh_time = refresh_time if refresh_time else time.time()
    # leaders = cards[(cards['set_code']==set_code) & (cards['card_type']=='Leader')].sort_values('card_id')
    with open(SQL / "leaders_for_pages.sql") as f: sql = f.read()
    sql = replace_text(
        {
            "%set_code": set_code,
            "%today": date.today().strftime('%Y-%m-%d')
        },
        sql
    )
    leaders = cards[cards["card_id"].isin(db.query(sql)["card_id"])]
    leader_html = read_file(HTML_PIECES / "leader.html")
    for leader in leaders.itertuples():
        logger.debug(f'Writing {leader.card_id}')
        card_grid_query = re.sub('%card_id', leader.card_id, read_file(SQL / "advanced_leader_query.sql"))  
        card_grid = db.query(card_grid_query)
        sub_map = {
            '%title': leader.title or '',
            '%subtitle': leader.subtitle or '',
            '%set_title': sets[sets['set_code']==set_code]['title'].values[0] or '',
            '%set_code': set_code or '',
            '%card_num': re.sub('_', '-', leader.card_id) or '',
            '%aspects': re.sub(',', ' ', leader.aspects) or '',
            '%traits': ' '.join([t.title() for t in leader.traits.split(',')]) or '',
            '%front_text': leader.front_text or '',
            '%back_text': leader.back_text or '',
            '%front_art': leader.front_art or '',
            '%back_art': leader.back_art or '',
            '%set_filters': '\n'.join([f'<option value=\"{set.set_code}\">{set.title}</option>' for set in sets.itertuples() if set.set_code in card_grid['set_code'].drop_duplicates().values]) or '',
            '%card_grid': get_leader_articles(card_grid=card_grid) or '',
            '%decks': str(db.query(f'SELECT COUNT(*) FROM deck_leaders WHERE card_id = \'{leader.card_id}\'').values[0][0]) or '',
            '%time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(refresh_time)) or '',
            '%card_id': leader.card_id or ''
        }
        write_file(HTML / f"{leader.set_code}/{leader.card_id}.html", replace_text(sub_map, leader_html[:]))
  
    
def write_leader_pages(refresh_time=None):
    refresh_time = refresh_time if refresh_time else time.time()
    sets = db.read('sets')
    cards = db.read('cards')
    for set in sets.itertuples():
        set_leaders = cards[(cards['set_code']==set.set_code) & (cards['card_type']=='Leader')].sort_values('card_id')
        if set_leaders.shape[0] > 0:
            logger.info(f'Writing HTML for {set.title} ({set.set_code})')
            write_set_leader_pages(sets, cards, set.set_code, refresh_time)


def write_about(refresh_time=None):
    logger.info('Writing About')
    refresh_time = refresh_time if refresh_time else time.time()
    about_html = read_file(HTML_PIECES / "about.html")
    sub = {
        '%time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(refresh_time))
    }
    write_file(HTML / "about.html", replace_text(sub, about_html[:]))

if __name__ == '__main__':
    t_0 = time.time()
    write_index(t_0)
    write_about(t_0)
    # write_set_leader_pages(db.read('sets'), db.read('cards'), 'LAW')
    write_leader_pages(t_0)
    t_1 = time.time()
    logger.success(f'RUN COMPLETE - {int(t_1 - t_0)}s')
