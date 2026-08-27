SELECT
    dl.card_id
FROM decks d
JOIN deck_leaders dl ON dl.deck_id = d.deck_id
JOIN cards c ON c.card_id = dl.card_id
JOIN sets s ON s.set_code = c.set_code
WHERE 
    c.card_type = 'Leader'
    AND c.set_code = '%set_code'
GROUP BY dl.card_id
HAVING
    MAX(d.date_inserted) = '%today'
ORDER BY 
    s.release_date DESC
    , c.card_id
;