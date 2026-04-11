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
    download.overhaul_sets()
    download.overhaul_cards()
    download.get_new_deck_ids()
    download.download_decks()
    html_writer.write_index()
    html_writer.write_leader_pages()

if __name__ == '__main__':
    t_0 = time.time()
    main()
    t_1 = time.time()
    logger.success(f'RUN COMPLETE - {int(t_1 - t_0)}s')