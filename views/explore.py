from __future__ import annotations

import html
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from phase2.backend import rank_market_segments
from .common import (INK, MISSING, MUTED, PRICE_SCALE, ROOM_COLORS, SHARE_SCALE, add_small_metric_flags,
                     keep, kept, metric_cards, number, panel_header, section, style_fig, table_formats,
                     usable_max)


STATIC = {"displayModeBar": False}


def _detail_from_plotly(key: str, set_detail) -> None:
    state = st.session_state.get(key)
    points = getattr(getattr(state, "selection", None), "points", []) if state is not None else []
    if not points:
        return
    point = points[0]
    custom = point.get("customdata")
    if custom:
        signature = (key, tuple(custom[:2]))
    else:
        signature = (key, point.get("point_index"), point.get("curve_number"))
    # Plotly keeps its last selection through ordinary reruns. Only accept a
    # newly observed point signature, so an older marker cannot undo Reset or
    # the keyboard selector on a later filter rerun.
    if st.session_state.get("last_map_selection") != signature:
        st.session_state.last_map_selection = signature
        set_detail(str(custom[0]) if custom else None)


def _room_chip(room: str) -> None:
    st.markdown(
        f'<div class="room-chip"><i style="background:{ROOM_COLORS.get(room, MUTED)}"></i>{html.escape(room)}</div>',
        unsafe_allow_html=True,
    )


def _map_fig(frame: pd.DataFrame, room: str, color_column: str, color_title: str,
             is_share: bool, online: bool):
    valid = frame.dropna(subset=["latitude", "longitude"]).copy()
    if valid.empty:
        return None
    value_max = 1.0 if is_share else usable_max(frame[color_column])
    count_values = sorted(valid.listing_count.astype(int).unique().tolist())
    if len(count_values) <= 3:
        legend_counts = count_values
    else:
        legend_counts = sorted({count_values[0], count_values[len(count_values) // 2], count_values[-1]})
    count_max = max(1, int(valid.listing_count.max()))
    sizeref = 2 * count_max / (42 ** 2)
    hover_columns = [
        "neighbourhood", "room_type", "listing_count", "map_n", "price_n", "median_price",
        "missing_price_n", "within_budget_n", "within_budget_share", "pre_budget_price_n",
    ]
    for column in hover_columns:
        if column not in valid.columns:
            valid[column] = pd.NA
    custom = valid[hover_columns].astype(object).where(valid[hover_columns].notna(), None).values.tolist()
    valid["_custom"] = custom
    valid["_metric_missing"] = valid[color_column].isna()

    fig = go.Figure()
    for missing in [False, True]:
        part = valid.loc[valid._metric_missing.eq(missing)]
        if part.empty:
            continue
        # A thin white ring separates overlapping markers.
        marker = dict(size=part.listing_count.astype(float), sizemode="area", sizeref=sizeref,
                      color=MISSING if missing else part[color_column].astype(float), opacity=.9,
                      line=dict(color="white", width=1.5))
        if not missing:
            marker.update(colorscale=SHARE_SCALE if is_share else PRICE_SCALE, cmin=0, cmax=value_max,
                          colorbar=dict(title=dict(text=color_title, side="right"), thickness=12, outlinewidth=0,
                                        tickformat=".0%" if is_share else "$,.0f"))
        trace_args = dict(
            mode="markers", marker=marker, customdata=part._custom.tolist(),
            name="Missing metric (gray)" if missing else room,
            hovertemplate=(
                "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                "Listings in map population: %{customdata[2]}<br>Valid coordinates (map_n): %{customdata[3]}<br>"
                "Selected median: $%{customdata[5]:,.0f}/night (price_n %{customdata[4]})<br>"
                "Selected missing prices: %{customdata[6]}<br>"
                "Pre-budget within budget: %{customdata[7]} of %{customdata[9]} priced "
                "(%{customdata[8]:.1%})<extra></extra>"
            ),
        )
        if online:
            fig.add_trace(go.Scattermap(lat=part.latitude.astype(float), lon=part.longitude.astype(float), **trace_args))
        else:
            fig.add_trace(go.Scatter(x=part.longitude.astype(float), y=part.latitude.astype(float), **trace_args))
    for count in legend_counts:
        marker = dict(size=count, sizemode="area", sizeref=sizeref, color="#DDDDDD", line=dict(color=MUTED, width=1))
        trace = go.Scattermap(lat=[None], lon=[None]) if online else go.Scatter(x=[None], y=[None])
        trace.update(mode="markers", marker=marker, name=f"{count:,} listings")
        fig.add_trace(trace)
    style_fig(fig, height=520)
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=60), clickmode="event+select", dragmode="pan",
        legend=dict(orientation="h", y=-0.12, title=dict(text="Marker area ∝ listing count  ")),
    )
    if online:
        lat_min, lat_max = float(valid.latitude.min()), float(valid.latitude.max())
        lon_min, lon_max = float(valid.longitude.min()), float(valid.longitude.max())
        span = max(lat_max - lat_min, lon_max - lon_min, 0.01)
        zoom = max(4, min(11, math.log2(360 / span) - 1))
        fig.update_layout(map=dict(style="carto-positron", zoom=zoom,
                                   center=dict(lat=(lat_min + lat_max) / 2, lon=(lon_min + lon_max) / 2)))
    else:
        fig.update_xaxes(title="Longitude (degrees)", showgrid=True)
        fig.update_yaxes(title="Latitude (degrees)", showgrid=True,
                         scaleanchor="x", scaleratio=1 / math.cos(math.radians(34)))
    return fig


def _bar_colorbar(title: str, **ticks) -> dict:
    """Thin horizontal color key above a bar chart, so half-width panels keep their plot width."""
    return dict(title=dict(text=title, side="top"), orientation="h", x=0, xanchor="left", y=1.02,
                yanchor="bottom", len=.6, thickness=8, outlinewidth=0, tickangle=0, nticks=4, **ticks)


def _price_bars(ranked: pd.DataFrame, shared_max: float, room: str):
    fig = px.bar(
        ranked, x="median_price", y="neighbourhood", orientation="h", color="median_price",
        color_continuous_scale=PRICE_SCALE, range_color=[0, shared_max],
        custom_data=["price_p25", "price_p75", "listing_count", "price_n", "missing_price_n"],
    )
    fig.update_traces(
        texttemplate="$%{x:,.0f}", textposition="outside", cliponaxis=False, textfont=dict(color=INK, size=12),
        hovertemplate=("<b>%{y}</b><br>Median: $%{x:,.0f}/night<br>Middle 50%: $%{customdata[0]:,.0f}–"
                       "$%{customdata[1]:,.0f}<br>Listings: %{customdata[2]:,} · price_n %{customdata[3]:,}"
                       "<br>Missing prices: %{customdata[4]:,}<extra></extra>"),
    )
    style_fig(fig, height=max(420, 28 * len(ranked) + 110))
    fig.update_layout(margin=dict(l=10, r=10, t=70, b=10))
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False)
    fig.update_xaxes(range=[0, shared_max * 1.15], title="Median listed price (USD/night)", tickprefix="$",
                     nticks=6, tickangle=0)
    fig.update_layout(coloraxis_colorbar=_bar_colorbar("Median USD/night", tickprefix="$"), bargap=.35)
    return fig


def _share_bars(ranked: pd.DataFrame, budget: float):
    fig = px.bar(
        ranked, x="within_budget_share", y="neighbourhood", orientation="h", color="within_budget_share",
        color_continuous_scale=SHARE_SCALE, range_color=[0, 1],
        custom_data=["within_budget_n", "price_n", "listing_count", "missing_price_n"],
    )
    fig.update_traces(
        texttemplate="%{x:.0%}", textposition="outside", cliponaxis=False, textfont=dict(color=INK, size=12),
        hovertemplate=(f"<b>%{{y}}</b><br>Within ${budget:,.0f}/night: %{{x:.1%}}<br>"
                       "%{customdata[0]:,} of %{customdata[1]:,} pre-budget observed prices"
                       "<br>Listings: %{customdata[2]:,} · missing prices %{customdata[3]:,}<extra></extra>"),
    )
    style_fig(fig, height=max(420, 28 * len(ranked) + 110))
    fig.update_layout(margin=dict(l=10, r=10, t=70, b=10))
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False)
    fig.update_xaxes(range=[0, 1.12], tickformat=".0%", tickvals=[0, .25, .5, .75, 1], tickangle=0,
                     title="Share of observed pre-budget prices")
    fig.update_layout(coloraxis_colorbar=_bar_colorbar("Share within budget", tickformat=".0%"), bargap=.35)
    return fig


def _segment_evidence(tables, filters, set_detail) -> None:
    # Selected segments carry no budget columns; the labeled pre-budget join
    # below is the only budget evidence shown in this table.
    selected = tables["segments"].drop(columns=["within_budget_n", "within_budget_share"])
    pre = tables["affordability_segments"].copy()
    if filters.budget_usd is not None:
        affordability = pre[["neighbourhood", "room_type", "within_budget_n", "within_budget_share", "price_n"]].rename(
            columns={"within_budget_n": "pre_budget_within_budget_n",
                     "within_budget_share": "pre_budget_within_budget_share",
                     "price_n": "pre_budget_price_n"}
        )
        selected = selected.merge(affordability, on=["neighbourhood", "room_type"], how="left", validate="one_to_one")
    else:
        selected["pre_budget_within_budget_n"] = pd.NA
        selected["pre_budget_within_budget_share"] = pd.NA
        selected["pre_budget_price_n"] = selected.price_n
    selected = add_small_metric_flags(selected)
    search = keep("segment_search", st.text_input(
        "Search neighborhood or room type", value=kept("segment_search", ""), key="segment_search",
        placeholder="e.g. Venice, Private room"))
    visible = selected
    if search.strip():
        needle = search.strip()
        visible = selected.loc[
            selected.neighbourhood.str.contains(needle, case=False, regex=False, na=False)
            | selected.room_type.str.contains(needle, case=False, regex=False, na=False)
        ]
    visible = visible.sort_values(["median_price", "neighbourhood", "room_type"], na_position="last").reset_index(drop=True)
    filter_signature = repr((filters.neighbourhoods, filters.room_types, filters.trip_nights,
                             filters.budget_usd, filters.min_reviews, filters.exclude_high_prices, search))
    key = "segment_table_" + str(abs(hash(filter_signature)))
    detail = st.session_state.get("detail_neighbourhood")
    styled = visible.style.apply(
        lambda row: ["background-color: #FFF0F0" if row.neighbourhood == detail else "" for _ in row], axis=1
    ).format(table_formats(visible), na_rep="N/A")
    event = st.dataframe(
        styled, hide_index=True, width="stretch", height=440,
        on_select="rerun", selection_mode="single-row", key=key,
    )
    rows = event.selection.rows if event is not None else []
    if rows:
        selected_area = str(visible.iloc[rows[0]].neighbourhood)
        signature = (key, selected_area)
        if st.session_state.get("last_segment_selection") != signature:
            st.session_state.last_segment_selection = signature
            set_detail(selected_area)
    st.caption("Select a row to focus Listings & methods on that neighborhood. Budget columns are pre-budget "
               "(computed before budget filtering). n<30 flags are display guidance, not statistical significance. "
               "Availability is source calendar context, not occupancy or trip confirmation.")


def render_explore(tables, filters, set_detail, room_views, detail_picker) -> None:
    rooms = filters.room_types or ()
    selected_count = len(tables["listings"])

    section("01 / Overview", "At a glance",
            "Each room type gets its own cards. Room types are never pooled into one price or budget figure.")
    if selected_count == 0:
        st.warning("No listings match these filters. Try a higher budget, a longer stay, fewer review "
                   "requirements, or press Reset in the sidebar.")
    if not rooms:
        metric_cards(tables["overview"].iloc[0], tables["affordability"].iloc[0], filters.budget_usd)
    for room in rooms:
        room_tables = room_views[room]
        overview = room_tables["overview"].iloc[0]
        affordability = room_tables["affordability"].iloc[0]
        if len(rooms) > 1:
            _room_chip(room)
        metric_cards(overview, affordability, filters.budget_usd)
    if len(rooms) == 1:
        overview = room_views[rooms[0]]["overview"].iloc[0]
        st.caption(f"{rooms[0]} · selected price_n={number(overview.price_n)}; missing selected prices="
                   f"{number(overview.missing_price_n)}. Reviewed-share denominator: "
                   f"{number(overview.listing_count)} selected listings.")
    elif len(rooms) > 1:
        st.caption(f"Mixed room types · {number(selected_count)} matching listings in total. "
                   "Prices and shares above are per room type only.")

    selected = tables["segments"]
    pre = tables["affordability_segments"]
    ranked_by_room = {
        room: rank_market_segments(selected.loc[selected.room_type.eq(room)], metric="median_price",
                                   min_n=30, ascending=True).head(15)
        for room in rooms
    }
    # One 0-to-max price scale shared by every room panel, sized to the bars shown.
    shared_max = usable_max(pd.concat([r.median_price for r in ranked_by_room.values()])
                            if ranked_by_room else pd.Series(dtype=float))
    section("02 / Prices", "Where your budget goes furthest",
            "Ranking bars need at least 30 observed prices per neighborhood. This is a display rule, not statistical significance.")
    for room in rooms:
        if len(rooms) > 1:
            _room_chip(room)
        part = selected.loc[selected.room_type.eq(room)]
        ranked = ranked_by_room[room]
        price_col, share_col = st.columns(2) if filters.budget_usd is not None else (st.container(), None)
        with price_col, st.container(key=f"panel_price_{room}"):
            missing = int(part.missing_price_n.sum()) if not part.empty else 0
            panel_header("Lowest median prices · selected listings",
                         f"15 most affordable neighborhoods · {room}",
                         f"Median listed USD/night. {number(part.listing_count.sum())} listings; "
                         f"{missing:,} with missing prices are excluded from price statistics.")
            if ranked.empty:
                st.info(f"No neighborhood has 30+ observed prices for {room} under these filters. "
                        "Widen the filters or see the evidence table below.")
            else:
                st.plotly_chart(_price_bars(ranked, shared_max, room), width="stretch", key=f"price_bars_{room}",
                                config=STATIC)
        if share_col is None:
            continue
        pre_part = pre.loc[pre.room_type.eq(room)]
        ranked_share = rank_market_segments(pre_part, metric="within_budget_share", min_n=30, ascending=False).head(15)
        with share_col, st.container(key=f"panel_share_{room}"):
            panel_header("Budget fit · pre-budget population",
                         f"Highest share within ${filters.budget_usd:,.0f}/night · {room}",
                         "Share of all observed prices (before the budget filter) at or below your budget.")
            if ranked_share.empty:
                st.info(f"No neighborhood has 30+ pre-budget observed prices for {room}.")
            else:
                st.plotly_chart(_share_bars(ranked_share, filters.budget_usd), width="stretch",
                                key=f"affordability_bars_{room}", config=STATIC)

    cdf = tables["price_distribution"]
    cdf = cdf.loc[cdf.room_type.isin(rooms)]
    with st.container(key="panel_cdf"):
        head, toggle = st.columns([4, 1], vertical_alignment="bottom")
        with head:
            panel_header("Price distribution, not a time trend · pre-budget population",
                         "What share of listings cost less than a given price?",
                         "Each step is an observed listed price. Read across from any price to the share of priced listings at or below it.")
        if cdf.empty:
            st.info("No observed prices are available for the selected pre-budget population, so no distribution can be drawn.")
        else:
            log_x = keep("cdf_log_x", toggle.toggle("Log price axis", value=kept("cdf_log_x", True), key="cdf_log_x"))
            # A log axis cannot place $0 listings; they still count in each cumulative share.
            plotted = cdf.loc[cdf.nightly_price_usd.gt(0)] if log_x else cdf
            fig = px.line(
                plotted, x="nightly_price_usd", y="cumulative_share", color="room_type", line_shape="hv",
                color_discrete_map=ROOM_COLORS, custom_data=["price_n"],
                labels={"room_type": "Room type"},
            )
            fig.update_traces(line=dict(width=2),
                              hovertemplate="<b>%{fullData.name}</b><br>$%{x:,.0f}/night or less: "
                                            "%{y:.1%} of %{customdata[0]:,} priced listings<extra></extra>")
            style_fig(fig, height=420)
            fig.update_yaxes(range=[0, 1.02], tickformat=".0%", title="Cumulative share of priced listings (0–100%)")
            if log_x and not plotted.empty:
                low, high = float(plotted.nightly_price_usd.min()), float(plotted.nightly_price_usd.max())
                ticks = [t for t in (1, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000)
                         if low <= t <= high]
                fig.update_xaxes(type="log", range=[math.log10(low), math.log10(max(high, low * 10))],
                                 title="Listed price (USD/night, logarithmic scale)",
                                 tickvals=ticks, ticktext=[f"${t:,}" for t in ticks])
            else:
                fig.update_xaxes(range=[0, usable_max(cdf.nightly_price_usd)], title="Listed price (USD/night)",
                                 tickprefix="$")
            if filters.budget_usd is not None:
                fig.add_trace(go.Scatter(
                    x=[filters.budget_usd, filters.budget_usd], y=[0, 1], mode="lines+text",
                    line=dict(color=INK, width=1.5, dash="dash"), name=f"Budget ${filters.budget_usd:,.0f}",
                    text=[f" Budget ${filters.budget_usd:,.0f}", ""], textposition="top right",
                    textfont=dict(color=INK, size=12), hoverinfo="skip", showlegend=False,
                ))
            fig.update_layout(legend=dict(orientation="h", y=1.08, x=0, title=None), hovermode="closest")
            st.plotly_chart(fig, width="stretch", key="price_cdf", config=STATIC)
            notes = []
            for room in rooms:
                room_rows = cdf.loc[cdf.room_type.eq(room)]
                if not room_rows.empty:
                    price_n = int(room_rows.price_n.iloc[0])
                    listings_n = int(pre.loc[pre.room_type.eq(room)].listing_count.sum())
                    notes.append(f"{room}: {price_n:,} observed prices, {listings_n - price_n:,} missing")
            st.caption(" · ".join(notes) + ". The log axis (default) spans the full observed range while keeping typical prices readable; switch it off for a linear scale.")

    section("03 / Map", "Neighborhoods on the map",
            "Each bubble is one neighborhood's approximate center. Click a bubble to focus the listing table.")
    with st.container(key="panel_map"):
        controls = st.columns([1.4, 1.4, 1], vertical_alignment="bottom")
        metric_options = ["Median listed USD/night", "Within-budget share · pre-budget"]
        metric = keep("map_metric", controls[0].selectbox(
            "Color bubbles by", metric_options, key="map_metric",
            index=metric_options.index(kept("map_metric", metric_options[0]))))
        with controls[1]:
            detail_picker()
        online = keep("online_basemap", controls[2].toggle(
            "Street basemap (online)", value=kept("online_basemap", False), key="online_basemap"))
        share_map = metric.startswith("Within-budget")
        if share_map and filters.budget_usd is None:
            st.info("Choose a nightly budget in the filter bar to color neighborhoods by budget fit.")
        else:
            source = tables["affordability_map"] if share_map else tables["map"]
            color_column = "within_budget_share" if share_map else "median_price"
            color_title = "Within budget" if share_map else "Median USD/night"
            population = "pre-budget" if share_map else "selected"
            for room in rooms:
                groups = source.loc[source.room_type.eq(room)]
                valid_n = int(groups.map_n.fillna(0).sum()) if not groups.empty else 0
                total_n = int(groups.listing_count.sum()) if not groups.empty else 0
                small = int(groups.price_n.lt(30).sum()) if not groups.empty else 0
                panel_header(f"{color_title} · {population} population", room,
                             f"{total_n - valid_n:,} listings omitted from centers (coordinates failed the map screen). "
                             f"{small:,} neighborhoods have price_n<30 and stay visible with their sample sizes in the tooltip.")
                fig = _map_fig(groups, room, color_column, color_title, share_map, online)
                if fig is None:
                    st.info(f"No mappable neighborhood centers for {room} under these filters.")
                    continue
                key = f"neighborhood_map_{room}_{'budget' if share_map else 'price'}"
                st.plotly_chart(fig, width="stretch", key=key, on_select="rerun", selection_mode="points",
                                config={"displaylogo": False, "scrollZoom": True,
                                        "modeBarButtonsToRemove": ["lasso2d", "select2d", "toImage"]})
                _detail_from_plotly(key, set_detail)
            st.caption(("Street basemap © OpenStreetMap contributors, © CARTO. " if online else
                        "Offline coordinate grid; axes are degrees. ")
                       + "Bubble centers are approximate means of listing coordinates, not listing pins, "
                         "official boundaries or density. Gray bubbles have no observed value for the chosen metric.")

    section("04 / Evidence", "Every neighborhood and room type",
            "Searchable and sortable. Small samples stay visible with flags.")
    with st.container(key="panel_segments"):
        _segment_evidence(tables, filters, set_detail)
