-- SQLite
SELECT
    dc.card_id
    ,c.set_code
    ,c.num
    ,c.title
    ,c.subtitle
    ,c.front_art
    ,c.aspects
    ,c.card_type
    ,stat.num_decks [tot_decks]
    ,COUNT(*) [num_decks]
    ,SUM(CASE WHEN dc.num = 3 THEN 1 ELSE 0 END) [copy3]
    ,SUM(CASE WHEN dc.num = 2 THEN 1 ELSE 0 END) [copy2]
    ,SUM(CASE WHEN dc.num = 1 THEN 1 ELSE 0 END) [copy1]
FROM deck_cards dc
JOIN deck_leaders dl ON dl.deck_id = dc.deck_id 
    AND dl.card_id LIKE '%%card_id%'
JOIN cards c ON dc.card_id = c.card_id
LEFT JOIN (
    SELECT 
        dl.card_id
        ,COUNT(dl.card_id) [num_decks]
    FROM deck_leaders dl
    GROUP BY dl.card_id
) AS stat ON dl.card_id = stat.card_id
GROUP BY dc.card_id
ORDER BY COUNT(dc.card_id) DESC
;