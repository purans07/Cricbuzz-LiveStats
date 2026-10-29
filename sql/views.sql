-- Supporting reads only. Q01-Q25 remain individual Phase 11 lessons.
CREATE VIEW v_active_players AS
SELECT * FROM players WHERE is_deleted = 0;

CREATE VIEW v_active_match_players AS
SELECT mp.* FROM match_players AS mp
JOIN v_active_players AS p ON p.player_id = mp.player_id;

CREATE VIEW v_active_batting AS
SELECT b.* FROM batting_performances AS b
JOIN v_active_players AS p ON p.player_id = b.player_id
JOIN innings AS i ON i.innings_id = b.innings_id
WHERE b.is_deleted = 0 AND i.is_super_over = 0;

CREATE VIEW v_active_bowling AS
SELECT b.* FROM bowling_performances AS b
JOIN v_active_players AS p ON p.player_id = b.player_id
JOIN innings AS i ON i.innings_id = b.innings_id
WHERE b.is_deleted = 0 AND i.is_super_over = 0;

CREATE VIEW v_active_fielding AS
SELECT f.* FROM fielding_performances AS f
JOIN v_active_players AS p ON p.player_id = f.player_id
JOIN innings AS i ON i.innings_id = f.innings_id
WHERE f.is_deleted = 0 AND i.is_super_over = 0;

-- Keep sources separate; a latest snapshot may still have unknown fields.
CREATE VIEW v_latest_career AS
SELECT c.*, b.source_id, b.fetched_at
FROM career_stats_snapshots AS c
JOIN import_batches AS b ON b.batch_id = c.batch_id
JOIN v_active_players AS p ON p.player_id = c.player_id
WHERE b.status = 'committed' AND NOT EXISTS (
    SELECT 1 FROM career_stats_snapshots AS newer
    JOIN import_batches AS nb ON nb.batch_id = newer.batch_id
    WHERE newer.player_id = c.player_id AND newer.format_id = c.format_id
      AND nb.source_id = b.source_id AND nb.status = 'committed'
      AND (nb.fetched_at > b.fetched_at
           OR (nb.fetched_at = b.fetched_at AND nb.batch_id > b.batch_id))
);
