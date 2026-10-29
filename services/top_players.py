"""Source-scoped leaderboards over latest committed career snapshots."""

from sqlalchemy import text

METRICS = {
    "Most runs": ("runs", "DESC"),
    "Highest score": ("highest_score", "DESC"),
    "Most wickets": ("wickets", "DESC"),
    "Batting average": ("batting_average", "DESC"),
    "Strike rate": ("strike_rate", "DESC"),
    "Bowling average": ("bowling_average", "ASC"),
    "Economy rate": ("economy", "ASC"),
}
METRIC_SQL = """
SELECT c.player_id,p.full_name AS player_name,p.external_id AS provider_player_id,
       c.matches_played,c.runs,c.highest_score,c.centuries,c.wickets,
       CASE WHEN c.dismissals>0 THEN 1.0*c.runs/c.dismissals
            WHEN c.dismissals IS NULL THEN c.reported_batting_average END AS batting_average,
       CASE WHEN c.balls_faced>0 THEN 100.0*c.runs/c.balls_faced
            WHEN c.balls_faced IS NULL THEN c.reported_strike_rate END AS strike_rate,
       CASE WHEN c.wickets>0 THEN 1.0*c.runs_conceded/c.wickets
            WHEN c.wickets IS NULL THEN c.reported_bowling_average END AS bowling_average,
       CASE WHEN c.legal_balls_bowled>0 THEN 6.0*c.runs_conceded/c.legal_balls_bowled
            WHEN c.legal_balls_bowled IS NULL THEN c.reported_economy END AS economy,
       c.fetched_at,b.completeness
FROM v_latest_career c JOIN players p ON p.player_id=c.player_id
JOIN import_batches b ON b.batch_id=c.batch_id
WHERE c.source_id=:source_id AND c.format_id=:format_id
  AND (:minimum_matches=0 OR c.matches_played>=:minimum_matches)
"""


class TopPlayersService:
    """No network calls, career summation or name-based identity merging."""

    def __init__(self, database):
        """Retain validated dependencies for this component without performing its operations."""
        self.database = database

    def catalog(self):
        """List only source/format combinations with active latest career data."""
        with self.database.transaction() as c:
            return [
                dict(r)
                for r in c.execute(
                    text("""
                SELECT s.source_id,s.name AS source_name,f.format_id,f.code AS format_code,
                       COUNT(*) AS players
                FROM v_latest_career v JOIN sources s ON s.source_id=v.source_id
                JOIN formats f ON f.format_id=v.format_id
                GROUP BY s.source_id,f.format_id ORDER BY s.name,f.code
            """)
                ).mappings()
            ]

    def leaders(self, source_id, format_id, metric, *, limit=10, minimum_matches=0):
        """Rank unrounded values, keep dense ties and cap rows deterministically."""
        if metric not in METRICS:
            raise ValueError("Choose a listed ranking measure.")
        for value, low, high in (
            (source_id, 1, 2**63 - 1),
            (format_id, 1, 2**63 - 1),
            (limit, 1, 100),
            (minimum_matches, 0, 100000),
        ):
            if type(value) is not int or not low <= value <= high:
                raise ValueError("Ranking filters are outside the supported range.")
        column, direction = METRICS[metric]
        params = {
            "source_id": source_id,
            "format_id": format_id,
            "limit": limit,
            "minimum_matches": minimum_matches,
        }
        # All interpolated identifiers/order tokens come from the fixed metric map.
        with self.database.transaction() as c:
            coverage = dict(
                c.execute(
                    text(f"""WITH metrics AS ({METRIC_SQL})
                SELECT COUNT(*) AS eligible_players,COUNT({column}) AS ranked_players,
                       MIN(fetched_at) AS oldest_import,MAX(fetched_at) AS newest_import
                FROM metrics"""),
                    params,
                )
                .mappings()
                .one()
            )
            rows = [
                dict(r)
                for r in c.execute(
                    text(f"""WITH metrics AS ({METRIC_SQL})
                SELECT DENSE_RANK() OVER (ORDER BY {column} {direction}) AS rank,
                       *,{column} AS ranking_value
                FROM metrics WHERE {column} IS NOT NULL
                ORDER BY {column} {direction},player_id LIMIT :limit"""),
                    params,
                ).mappings()
            ]
            return {"coverage": coverage, "rows": rows}
