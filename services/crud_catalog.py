"""Read-only catalogs for administrative record and relationship selection."""

from sqlalchemy import text

from services.match_stats import table_for


class CrudCatalog:
    def __init__(self, database):
        """Retain validated dependencies for this component without performing its operations."""
        self.database = database

    def players(self):
        """List active player choices used by administrative forms."""
        with self.database.transaction() as c:
            return [
                dict(r)
                for r in c.exec_driver_sql(
                    "SELECT * FROM players ORDER BY player_id"
                ).mappings()
            ]

    def roles(self):
        """Read the available playing-role choices for validated forms."""
        with self.database.transaction() as c:
            return dict(
                c.exec_driver_sql(
                    "SELECT role_id,name FROM playing_roles ORDER BY name"
                ).all()
            )

    def records(self, kind):
        """Read supported statistic records for the chosen administrative category."""
        table = table_for(kind)
        with self.database.transaction() as c:
            return [
                dict(r)
                for r in c.exec_driver_sql(
                    f"SELECT s.*,p.full_name FROM {table} s JOIN players p ON p.player_id=s.player_id ORDER BY s.match_id,s.innings_id,s.player_id"
                ).mappings()
            ]

    def eligible(self, kind):
        """Return valid relationship choices for the requested statistic operation."""
        table_for(kind)
        side = (
            "batting_team_id"
            if kind == "batting"
            else "bowling_team_id"
            if kind == "bowling"
            else "bowling_team_id"
        )
        condition = f" AND mp.team_id=i.{side}" if side else ""
        with self.database.transaction() as c:
            return [
                dict(r)
                for r in c.execute(
                    text(f"""SELECT i.innings_id,i.innings_number,i.match_id,mp.team_id,
                p.player_id,p.full_name,m.description FROM innings i
                JOIN matches m ON m.match_id=i.match_id
                JOIN match_players mp ON mp.match_id=i.match_id
                JOIN v_active_players p ON p.player_id=mp.player_id
                WHERE 1=1 {condition} ORDER BY i.match_id,i.innings_number,p.player_id""")
                ).mappings()
            ]
