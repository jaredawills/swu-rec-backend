DROP TABLE IF EXISTS sets;

CREATE TABLE IF NOT EXISTS sets (
    set_code VARCHAR(5) PRIMARY KEY
    ,title VARCHAR(50)
    ,release_date VARCHAR(10)
);