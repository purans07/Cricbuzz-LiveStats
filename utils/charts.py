"""Plotly figures over existing result rows; no database calls or metric rewrites."""

from html import escape

import plotly.graph_objects as go

COLORS = ["#087F6B", "#3266A8", "#B7791F", "#8057A6", "#C45367", "#437F91"]


def _style(figure, title, context):
    """Apply consistent chart colors, typography and source context."""
    figure.update_layout(
        title={"text": escape(title) + "<br><sup>" + escape(context) + "</sup>"},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F3F6FA",
        font={"color": "#172B44", "family": "Arial, sans-serif", "size": 13},
        margin={"t": 90, "l": 20, "r": 20, "b": 55},
        legend={"orientation": "h"},
        hovermode="closest",
        height=440,
    )
    return figure


def player_label(row):
    """Build a stable player label that distinguishes duplicate display names."""
    return f"{row['player_name']} · #{row['player_id']}"


def ranking_bar(rows, metric, context):
    """Build a bounded ranking bar chart without changing source metric values."""
    rows = rows[:20]
    fig = go.Figure(
        go.Bar(
            x=[r["ranking_value"] for r in rows],
            y=[player_label(r) for r in rows],
            orientation="h",
            marker_color=COLORS[0],
            customdata=[
                [r["rank"], r["matches_played"], r["fetched_at"]] for r in rows
            ],
            hovertemplate="%{y}<br>Value: %{x}<br>Rank: %{customdata[0]}<br>Matches: %{customdata[1]}<br>Imported: %{customdata[2]}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", title="Player (stable local ID)")
    fig.update_xaxes(title=metric, rangemode="tozero")
    fig.update_layout(height=max(360, 90 + 28 * len(rows)))
    styled = _style(fig, metric, context)
    styled.update_layout(height=max(360, 130 + 28 * len(rows)))
    return styled


def player_comparison(rows, field, title, context):
    """Compare selected players on one measure, preserving unknown statistics."""
    fig = go.Figure(
        go.Bar(
            x=[player_label(r) for r in rows],
            y=[r[field] for r in rows],
            marker_color=COLORS[: len(rows)],
            hovertemplate="%{x}<br>%{y}<extra></extra>",
        )
    )
    fig.update_xaxes(title="Selected players")
    fig.update_yaxes(title=title, rangemode="tozero")
    return _style(fig, title, context)


def quarter_grid(rows):
    """Make absent calendar quarters explicit None cells, never zero or a bridge."""
    if not rows:
        return [], [], [], {}
    indices = [r["year"] * 4 + r["quarter"] - 1 for r in rows]
    quarters = list(range(min(indices), max(indices) + 1))
    labels = [f"{q // 4} Q{q % 4 + 1}" for q in quarters]
    players = list(dict.fromkeys(r["player_id"] for r in rows))
    lookup = {(r["player_id"], r["year"] * 4 + r["quarter"] - 1): r for r in rows}
    return quarters, labels, players, lookup


def quarterly_line(rows, field, title, context):
    """Build an ordered quarterly trend with missing periods represented as gaps."""
    quarters, labels, players, lookup = quarter_grid(rows)
    fig = go.Figure()
    for index, pid in enumerate(players):
        first = next(r for r in rows if r["player_id"] == pid)
        values = [lookup.get((pid, q), {}).get(field) for q in quarters]
        counts = [lookup.get((pid, q), {}).get("batting_matches") for q in quarters]
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=values,
                name=player_label(first),
                mode="lines+markers",
                connectgaps=False,
                line={"color": COLORS[index % len(COLORS)]},
                customdata=counts,
                hovertemplate="%{x}<br>Value: %{y}<br>Batting matches: %{customdata}<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_xaxes(
        title="Calendar quarter (UTC match starts)",
        categoryorder="array",
        categoryarray=labels,
    )
    fig.update_yaxes(title=title, rangemode="tozero")
    return _style(fig, title, context)


def quarterly_heatmap(rows, field, title, context):
    """Build a player-quarter heatmap without treating missing values as zeros."""
    quarters, labels, players, lookup = quarter_grid(rows)
    names = [
        player_label(next(r for r in rows if r["player_id"] == pid)) for pid in players
    ]
    values = [
        [lookup.get((pid, q), {}).get(field) for q in quarters] for pid in players
    ]
    fig = go.Figure(
        go.Heatmap(
            x=labels,
            y=names,
            z=values,
            colorscale=[[0, "#131C2E"], [1, "#14B8A6"]],
            colorbar={"title": title},
            hoverongaps=False,
            hovertemplate="%{y}<br>%{x}<br>%{z}<extra></extra>",
        )
    )
    fig.update_xaxes(title="Calendar quarter")
    fig.update_yaxes(title="Player (stable local ID)")
    return _style(fig, title, context)


def consistency_scatter(rows, context):
    """Compare observed batting means and dispersion with qualification context."""
    known = [
        (i, r)
        for i, r in enumerate(rows, 1)
        if r["average_runs"] is not None and r["standard_deviation_runs"] is not None
    ]
    fig = go.Figure(
        go.Scatter(
            x=[r["average_runs"] for _, r in known],
            y=[r["standard_deviation_runs"] for _, r in known],
            mode="markers",
            marker={"color": COLORS[1], "size": 11},
            text=[f"{r['player_name']} · result row {i}" for i, r in known],
            customdata=[r["eligible_innings"] for _, r in known],
            hovertemplate="%{text}<br>Mean runs: %{x}<br>Population deviation: %{y}<br>Innings: %{customdata}<extra></extra>",
        )
    )
    fig.update_xaxes(title="Mean qualifying innings runs", rangemode="tozero")
    fig.update_yaxes(title="Population standard deviation (runs)", rangemode="tozero")
    return _style(fig, "Scoring level and consistency", context)


def venue_bar(rows, field, title, context):
    # Unique result-row labels preserve SQL grain even with same-named identities.
    """Compare bounded venue results with distinct labels and original units."""
    shown = [(i, r) for i, r in enumerate(rows, 1) if r[field] is not None][:20]
    labels = [f"{r['player_name']} / {r['venue_name']} · row {i}" for i, r in shown]
    fig = go.Figure(
        go.Bar(
            x=[r[field] for _, r in shown],
            y=labels,
            orientation="h",
            marker_color=COLORS[0],
            customdata=[r["matches_played"] for _, r in shown],
            hovertemplate="%{y}<br>Value: %{x}<br>Qualifying matches: %{customdata}<extra></extra>",
        )
    )
    fig.update_xaxes(title=title, rangemode="tozero")
    fig.update_yaxes(title="Separate player–venue result rows", autorange="reversed")
    fig = _style(fig, title, context)
    fig.update_layout(height=max(400, 130 + 35 * len(shown)))
    return fig
