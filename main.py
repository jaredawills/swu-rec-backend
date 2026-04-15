# -*- coding: utf-8 -*-
"""
Created on Apr 09, 2026

@author: jared
"""

import time
from loguru import logger

import download
import html_writer

def main():
    logger.info('OVERHAUL SETS')
    download.overhaul_sets()
    logger.info('OVERHAUL CARDS')
    download.overhaul_cards()
    logger.info('GET NEW DECK IDS')
    download.get_new_deck_ids()
    logger.info('DOWNLOAD DECKS')
    download.download_decks()
    logger.info('WRITE INDEX')
    html_writer.write_index()
    logger.info('WRITE LEADER PAGES')
    html_writer.write_leader_pages()

if __name__ == '__main__':
    t_0 = time.time()
    main()
    t_1 = time.time()
    logger.success(f'RUN COMPLETE - {int(t_1 - t_0)}s')