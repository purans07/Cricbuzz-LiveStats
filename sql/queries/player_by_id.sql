-- The player_id parameter is bound by the caller, never interpolated.
SELECT player_id, full_name, role_id, batting_style, bowling_style,
       ownership, version, updated_at
FROM v_active_players WHERE player_id = :player_id;
