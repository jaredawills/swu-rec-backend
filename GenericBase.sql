-- SQLite
SELECT 
    SUBSTR(c.aspects, 1, 3) || '30' [card_id]
    ,c.aspects || ' Generic Base' [title]
    ,MAX(c.card_type) [card_type]
    ,MAX(front_art) [front_art]
FROM cards c
WHERE c.card_type = 'Base'
AND c.hp LIKE 30
GROUP BY c.aspects
;

SELECT 
    SUBSTR(c.aspects, 1, 3) || '28F' [card_id]
    ,c.aspects || ' Force Base' [title]
    ,MAX(c.card_type) [card_type]
    ,MAX(front_art) [front_art]
FROM cards c
WHERE c.card_type = 'Base'
AND c.hp LIKE 28
AND c.front_text LIKE '%FORCE unit attacks%'
GROUP BY c.aspects
;

SELECT 
    SUBSTR(c.aspects, 1, 3) || '27B' [card_id]
    ,c.aspects || ' Splash Base' [title]
    ,MAX(c.card_type) [card_type]
    ,MAX(front_art) [front_art]
FROM cards c
WHERE c.card_type = 'Base'
AND c.hp LIKE 27
AND c.front_text LIKE '%Play a card from your hand, ignoring 1 of its%'
GROUP BY c.aspects
;


-- SELECT 
--     SUBSTR(c.aspects, 1, 3) || '%ind' [card_id]
--     ,c.aspects || ' %title' [title]
--     ,MAX(c.card_type) [card_type]
--     ,MAX(front_art) [front_art]
-- FROM cards c
-- WHERE c.card_type = 'Base'
-- %filter
-- GROUP BY c.aspects
-- ;