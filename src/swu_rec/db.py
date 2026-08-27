# -*- coding: utf-8 -*-
"""
Created on Aug 19, 2026

@author: jared
"""

import sqlite3 as sql
import ast
from importlib.resources import files
from pathlib import Path

import pandas as pd
from loguru import logger

DATA_DIR = files("swu_rec") / "data"
SQL_DIR = DATA_DIR / "sql"
DB = DATA_DIR / "swurec.db"

def create_tables():
    directory_path = Path(SQL_DIR / "tables")
    tables = [f.stem for f in directory_path.iterdir() if f.is_file()]
    for table in tables:
        clear_table(table)
                   
                   
def list_tables():
    with sql.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for c in cursor:
            print(c)


def clear_table(table):
    with open(SQL_DIR / f'tables/{table}.sql', 'rt') as file:
        sql_script = file.read()
    with sql.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()


def insert_into(table, columns, rows):
    if len(rows) > 0 and len(columns) > 0:
        with sql.connect(DB) as conn:
            output = f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES "
            for row in rows:
                insert_row = '('
                values = []
                for value in row:
                    value = str(value)
                    value = '' if value == 'nan' else value
                    if len(value) > 0:
                        if value[0] == '[' and value[-1] == ']':
                            tmp = ast.literal_eval(value)
                            value = ','.join(tmp)
                        value = value.replace('\'', '\'\'')
                        values.append(f'\'{value}\'')
                    else:
                        values.append('NULL')
                insert_row += ','.join(values)
                insert_row += '),'
                output += insert_row 
            conn.execute(output[:-1])
            conn.commit()
    

def get_cols(table):
    conn = sql.connect(DB)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table});")
    output = []
    for c in cursor:
        output.append(c[1])
    return output
      

def get_conn():
    return sql.connect(DB)


def read(table):
    with sql.connect(DB) as conn:
        return pd.read_sql(f'SELECT * FROM {table};', conn)


def write(df, table):
    with sql.connect(DB) as conn:
        df.to_sql(table, conn, if_exists='replace', index=False)
        conn.commit()

def append(df, table):
    with sql.connect(DB) as conn:
        df.to_sql(table, conn, if_exists='append', index=False)
        conn.commit()

def query(query):
    with sql.connect(DB) as conn:
        return pd.read_sql(query, conn)

def drop_duplicates():
    for table in ["cards", "deck_cards", "deck_leaders", "decks", "sets", "historic_swudb", "historic_sw_unlimited_db"]:
        df = read(table)
        df = df.drop_duplicates()
        write(df, table)


if __name__ == '__main__':
    # # Will Drop and Create Tables, effectively resetting the ENTIRE database
    # create_tables()
    # list_tables()
    logger.success('RUN COMPLETE')