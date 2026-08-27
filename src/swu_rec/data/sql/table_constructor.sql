-- SQLite

DROP TABLE IF EXISTS cards;
DROP TABLE IF EXISTS deck_leaders;
DROP TABLE IF EXISTS deck_bases;
DROP TABLE IF EXISTS deck_cards; 

CREATE TABLE IF NOT EXISTS cards (
    card_id VARCHAR(10) PRIMARY KEY
    ,set_code VARCHAR(5)
    ,num INT
    ,title VARCHAR(50)
    ,subtitle VARCHAR(50)
    ,card_type VARCHAR(20)
    ,aspects varchar(50)
    ,traits VARCHAR(50)
    ,arenas VARCHAR(30)
    ,cost INT
    ,power INT
    ,hp INT
    ,front_text VARCHAR(1000)
    ,front_art VARCHAR(100)
    ,epic_action VARCHAR(500)
    ,double_sided INT
    ,back_text VARCHAR(1000)
    ,back_art VARCHAR(100)
    ,rarity VARCHAR(10)
    ,is_unique INT
    ,keywords VARCHAR(100)
    ,artist VARCHAR(50)
    ,variant_type VARCHAR(15)
);

CREATE TABLE IF NOT EXISTS deck_leaders (
    deck_id INT
    ,card_id VARCHAR(5)
);    

CREATE TABLE IF NOT EXISTS deck_bases (
    deck_id INT
    ,card_id VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS deck_cards (
    deck_id INT
    ,card_id VARCHAR(5)
    ,num INT
);
