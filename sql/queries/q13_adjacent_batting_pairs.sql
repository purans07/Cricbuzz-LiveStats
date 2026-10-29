-- Q13: Adjacent batting positions with combined individual innings runs >= 100.
SELECT
    a.match_id,
    a.innings_id,
    i.innings_number,
    p1.full_name AS player1_name,
    p2.full_name AS player2_name,
    a.runs + b.runs AS combined_runs
FROM v_active_batting AS a
JOIN v_active_batting AS b
    ON b.innings_id = a.innings_id
   AND b.batting_position = a.batting_position + 1
JOIN players AS p1 ON p1.player_id = a.player_id
JOIN players AS p2 ON p2.player_id = b.player_id
JOIN innings AS i ON i.innings_id = a.innings_id
WHERE a.runs + b.runs >= 100
ORDER BY combined_runs DESC, a.match_id ASC, a.innings_id ASC,
         a.batting_position ASC;
