# -*- coding: utf-8 -*-
"""
Created on Apr 09, 2026

@author: jared
"""

import sqlite3 as sql
import ast
import pandas as pd
from loguru import logger

def create_tables():
    with open('table_constructor.sql', 'rt') as file:
        sql_script = file.read()
    with sql.connect('swurec.db') as conn:
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()
                   
                   
def list_tables():
    with sql.connect('swurec.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for c in cursor:
            print(c)


def clear_table(table):
    with open(f'tables/{table}.sql', 'rt') as file:
        sql_script = file.read()
    with sql.connect('swurec.db') as conn:
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()


def insert_into(table, columns, rows):
    if len(rows) > 0 and len(columns) > 0:
        with sql.connect('swurec.db') as conn:
            cursor = conn.cursor()
            output = f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES "
            for row in rows:
                insert_row = '('
                values = []
                for column, value in zip(columns, row):
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
    conn = sql.connect('swurec.db')
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table});")
    output = []
    for c in cursor:
        output.append(c[1])
    return output
      

def get_conn():
    return sql.connect('swurec.db')


def read(table):
    with sql.connect('swurec.db') as conn:
        return pd.read_sql(f'SELECT * FROM {table};', conn)


def write(df, table):
    with sql.connect('swurec.db') as conn:
        df.to_sql(table, conn, if_exists='replace', index=False)
        conn.commit()


def query(query):
    with sql.connect('swurec.db') as conn:
        return pd.read_sql(query, conn)
        

if __name__ == '__main__':
    # # Will Drop and Create Tables, effectively resetting the ENTIRE database
    # create_tables()
    # list_tables()
    logger.success('RUN COMPLETE')