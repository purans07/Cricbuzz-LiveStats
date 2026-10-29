"""Explain and render chart choices without changing the underlying SQL metrics."""

from datetime import date

import pandas as pd
import streamlit as st

from services.analytics import AnalyticsError
from utils.charts import (
    consistency_scatter,
    player_comparison,
    quarterly_heatmap,
    quarterly_line,
    ranking_bar,
    venue_bar,
)


def leaderboard_charts(rows, metric, context):
    """Render source-scoped career ranking and optional separate-unit comparisons."""
    st.subheader("Career ranking chart")
    st.caption(
        "Bars make magnitudes easy to compare. The chart shows the first 20 displayed rows in table order; the table retains the full selected row cap. Lower is better for bowling average/economy. Hover for sample size and import time."
    )
    st.plotly_chart(
        ranking_bar(rows, metric, context), width="stretch", key="leaderboard_bar"
    )
    with st.expander("Compare players", expanded=False):
        options = [r["player_id"] for r in rows]
        selected = st.multiselect(
            "Compare displayed players",
            options,
            default=options[:2],
            max_selections=6,
            format_func=lambda pid: next(
                f"{r['player_name']} · #{pid}" for r in rows if r["player_id"] == pid
            ),
            key="chart_compare_players",
        )
        if len(selected) < 2:
            st.info(
                "Select at least two imported players for a comparison. A one-player dataset cannot establish relative performance."
            )
            return
        comparison = [r for r in rows if r["player_id"] in selected]
        st.caption(
            "Comparisons use only the displayed source/format and selected latest snapshots. Runs and wickets have separate axes and are never added or normalized together. Missing values produce no bar."
        )
        for field, title in [("runs", "Career runs"), ("wickets", "Career wickets")]:
            st.plotly_chart(
                player_comparison(comparison, field, title, context),
                width="stretch",
                key="compare_" + field,
            )


def render_visualizations(service):
    """Render reviewed quarterly, consistency and venue analyses from saved data."""
    st.subheader("Visualizations")
    st.caption(
        "These charts reuse the reviewed saved SQL results. No provider request is made. Sample records are fictional; provider history may not meet the eligibility rules."
    )
    view = st.selectbox(
        "Chart analysis",
        [
            "Quarterly trends and heatmap (Q25)",
            "Consistency scatter (Q19)",
            "Venue comparison (Q14)",
        ],
        key="viz_analysis",
    )
    context = f"{service.database.settings.data_mode.upper()} dataset · stored match history · all formats combined"
    try:
        if view.startswith("Quarterly"):
            day = st.date_input(
                "Trend analysis date (UTC)",
                value=date(2026, 10, 1),
                min_value=date(2000, 1, 1),
                max_value=date(2100, 12, 31),
                key="viz_date",
            )
            result = service.run_saved("Q25", day.isoformat())
        else:
            result = service.run_saved(
                "Q19" if view.startswith("Consistency") else "Q14", "2026-10-01"
            )
    except AnalyticsError as error:
        st.warning(str(error))
        return
    if result["truncated"]:
        st.warning(
            "The 500-row/output cap was reached. Charts use this clipped result, not complete history."
        )
    context += f" · revision {result['revision']}"
    rows = [
        dict(zip(result["columns"], values, strict=True)) for values in result["rows"]
    ]
    if not rows:
        st.info(
            "No qualifying saved data for this chart. An empty chart is not evidence of no real-world history. Try the sample dataset to explore the teaching fixtures."
        )
        return
    if view.startswith("Quarterly"):
        choices = list(dict.fromkeys(r["player_id"] for r in rows))
        selected = st.multiselect(
            "Players in quarterly charts",
            choices,
            default=choices[:2],
            max_selections=6,
            format_func=lambda pid: next(
                f"{r['player_name']} · #{pid}" for r in rows if r["player_id"] == pid
            ),
            key="viz_quarter_players",
        )
        filtered = [r for r in rows if r["player_id"] in selected]
        if not filtered:
            st.info("Choose at least one eligible player.")
            return
        label = st.selectbox(
            "Quarterly measure",
            ["Average runs per batting match", "Mean match strike rate"],
            key="viz_quarter_measure",
        )
        field = "average_runs" if label.startswith("Average") else "average_strike_rate"
        st.caption(
            "Q25 requires six observed quarters and three batting matches in every observed quarter in the twelve completed-quarter window. Lines show changes over time; the heatmap reveals high/low quarters. Gaps remain blank and are not joined or zero-filled. Mixed formats and incomplete imports can affect trends; these are not forecasts."
        )
        context += f" · window ending before current quarter of {day.isoformat()}"
        st.plotly_chart(
            quarterly_line(filtered, field, label, context),
            width="stretch",
            key="quarter_line",
        )
        st.plotly_chart(
            quarterly_heatmap(filtered, field, label, context),
            width="stretch",
            key="quarter_heatmap",
        )
    elif view.startswith("Consistency"):
        filtered = rows
        st.caption(
            "Q19 uses known innings scores with at least 10 balls faced, starting in 2022. Each point is one SQL result row; same-named players are not merged. Lower deviation means steadier scores, not necessarily better batting. Hover for innings count; a single innings has deviation zero without proving consistency."
        )
        st.plotly_chart(
            consistency_scatter(rows, context),
            width="stretch",
            key="consistency_scatter",
        )
    else:
        label = st.selectbox(
            "Venue measure",
            ["Average economy (runs per over)", "Total wickets"],
            key="viz_venue_measure",
        )
        field = (
            "average_economy_rate" if label.startswith("Average") else "total_wickets"
        )
        filtered = rows
        st.caption(
            "Q14 uses at least three qualifying matches per player/venue, each with at least 24 legal balls. Economy is the mean of those match economies. Bars preserve separate result rows and show the first 20 known values in SQL order, not a new ranking. Same-named identities are not aggregated; hover for match counts. Lower economy is better; more wickets can reflect greater opportunity."
        )
        st.plotly_chart(
            venue_bar(rows, field, label, context), width="stretch", key="venue_bar"
        )
    with st.expander("Chart source rows"):
        st.dataframe(pd.DataFrame(filtered), hide_index=True, width="stretch")
    st.caption(
        "Pie charts suit a complete, mutually exclusive whole. These rankings and overlapping/missing career or venue records do not establish that whole, so a pie chart would imply unsupported shares."
    )
