from __future__ import annotations

import html
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from phase2.backend import rank_market_segments
from .common import (CORAL, INK, LANDMARKS, MISSING, MUTED, PRICE_SCALE, ROOM_COLORS, SHARE_SCALE, airbnb_search,
                     keep, kept, metric_cards, miles, number, panel_header, pct, section, style_fig, usable_max,
                     usd)


STATIC = {"displayModeBar": False}
LA = (34.05, -118.24)


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


def _with_distances(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for name, point in LANDMARKS.items():
        out[f"mi_{name}"] = [miles(lat, lon, point) for lat, lon in zip(out.latitude, out.longitude)]
    return out


def _map_fig(frame: pd.DataFrame, color_column: str, color_title: str, is_share: bool, focus: str | None):
    """Neighborhood bubbles on a street basemap of Los Angeles; the focused neighborhood is ringed."""
    valid = _with_distances(frame.dropna(subset=["latitude", "longitude"]))
    if valid.empty:
        return None
    # Cap price color at the 95th percentile so a few tiny luxury groups don't wash out the rest;
    # capped bubbles show the darkest shade and their exact price on hover.
    prices = pd.to_numeric(frame[color_column], errors="coerce").dropna()
    value_max = 1.0 if is_share else (float(prices.quantile(.95)) if len(prices) else 1.0) or 1.0
    count_max = max(1, int(valid.listing_count.max()))
    sizeref = 2 * count_max / (40 ** 2)
    hover_columns = ["neighbourhood", "room_type", "listing_count", "median_price", "within_budget_n",
                     "pre_budget_price_n", "within_budget_share", *[f"mi_{n}" for n in LANDMARKS]]
    for column in hover_columns:
        if column not in valid.columns:
            valid[column] = pd.NA
    valid["_custom"] = valid[hover_columns].astype(object).where(valid[hover_columns].notna(), None).values.tolist()
    budget_line = ("<br>Fits your budget: %{customdata[6]:.0%} (%{customdata[4]} of %{customdata[5]})"
                   if is_share or valid.within_budget_n.notna().any() else "")
    fig = go.Figure()
    for missing in [False, True]:
        part = valid.loc[valid[color_column].isna().eq(missing)]
        if part.empty:
            continue
        marker = dict(size=part.listing_count.astype(float), sizemode="area", sizeref=sizeref, sizemin=4,
                      color=MISSING if missing else part[color_column].astype(float), opacity=.85)
        if not missing:
            marker.update(colorscale=SHARE_SCALE if is_share else PRICE_SCALE, cmin=0, cmax=value_max,
                          colorbar=dict(title=dict(text=color_title, side="right"), thickness=10, outlinewidth=0,
                                        tickformat=".0%" if is_share else "$,.0f", len=.8))
        fig.add_trace(go.Scattermap(
            lat=part.latitude.astype(float), lon=part.longitude.astype(float), mode="markers", marker=marker,
            customdata=part._custom.tolist(), name="No price data" if missing else color_title,
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[2]} places · typical "
                           "$%{customdata[3]:,.0f}/night" + budget_line +
                           "<br>Straight-line: %{customdata[7]:.0f} mi to Downtown · %{customdata[8]:.0f} mi to "
                           "Santa Monica beach · %{customdata[9]:.0f} mi to LAX<extra></extra>"),
            showlegend=missing,
        ))
    lat_min, lat_max = float(valid.latitude.min()), float(valid.latitude.max())
    lon_min, lon_max = float(valid.longitude.min()), float(valid.longitude.max())
    span = max(lat_max - lat_min, lon_max - lon_min, 0.01)
    center, zoom = dict(lat=(lat_min + lat_max) / 2, lon=(lon_min + lon_max) / 2), math.log2(360 / span) - .6
    focused = valid.loc[valid.neighbourhood.eq(focus)] if focus else valid.iloc[:0]
    if not focused.empty:
        spot = focused.iloc[0]
        fig.add_trace(go.Scattermap(
            lat=[float(spot.latitude)], lon=[float(spot.longitude)], mode="markers+text",
            marker=dict(size=34, color=INK, opacity=.28), text=[str(spot.neighbourhood)],
            textposition="top center", textfont=dict(size=14, color=INK), hoverinfo="skip", showlegend=False,
        ))
        center, zoom = dict(lat=float(spot.latitude), lon=float(spot.longitude)), 11
    style_fig(fig, height=540)
    fig.update_layout(
        map=dict(style="carto-positron", zoom=max(4, min(12, zoom)), center=center),
        margin=dict(l=0, r=0, t=0, b=0), clickmode="event+select",
        legend=dict(orientation="h", x=0, y=0, bgcolor="rgba(255,255,255,.8)"),
    )
    return fig, (lat_min, lat_max, lon_min, lon_max)


def _usa_locator(bounds) -> go.Figure:
    """Small USA map with state lines showing where the LA view sits."""
    lat_min, lat_max, lon_min, lon_max = bounds
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lon=[lon_min, lon_max, lon_max, lon_min, lon_min], lat=[lat_min, lat_min, lat_max, lat_max, lat_min],
        mode="lines", line=dict(color=CORAL, width=2), hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scattergeo(
        lon=[LA[1]], lat=[LA[0]], mode="markers+text", text=["Los Angeles"], textposition="middle right",
        textfont=dict(color=INK, size=13), marker=dict(color=CORAL, size=11, line=dict(color="white", width=2)),
        hoverinfo="skip", showlegend=False,
    ))
    fig.update_layout(
        geo=dict(scope="usa", projection_type="albers usa", showland=True, landcolor="#F2F2F2",
                 showsubunits=True, subunitcolor="#C8C8C8", subunitwidth=.8, showcountries=False,
                 showlakes=False, bgcolor="rgba(0,0,0,0)"),
        height=210, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _bar_colorbar(title: str, **ticks) -> dict:
    """Thin horizontal color key above a bar chart, so half-width panels keep their plot width."""
    return dict(title=dict(text=title, side="top"), orientation="h", x=0, xanchor="left", y=1.02,
                yanchor="bottom", len=.6, thickness=8, outlinewidth=0, tickangle=0, nticks=4, **ticks)


def _price_bars(ranked: pd.DataFrame, shared_max: float):
    fig = px.bar(
        ranked, x="median_price", y="neighbourhood", orientation="h", color="median_price",
        color_continuous_scale=PRICE_SCALE, range_color=[0, shared_max],
        custom_data=["price_p25", "price_p75", "listing_count"],
    )
    fig.update_traces(
        texttemplate="$%{x:,.0f}", textposition="outside", cliponaxis=False, textfont=dict(color=INK, size=12),
        hovertemplate=("<b>%{y}</b><br>Typical: $%{x:,.0f}/night<br>Most places: $%{customdata[0]:,.0f}–"
                       "$%{customdata[1]:,.0f}<br>%{customdata[2]:,} places<extra></extra>"),
    )
    style_fig(fig, height=max(420, 28 * len(ranked) + 110))
    fig.update_layout(margin=dict(l=10, r=10, t=70, b=10),
                      coloraxis_colorbar=_bar_colorbar("Price per night", tickprefix="$"), bargap=.35)
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False)
    fig.update_xaxes(range=[0, shared_max * 1.15], title="Typical price per night", tickprefix="$",
                     nticks=6, tickangle=0)
    return fig


def _share_bars(ranked: pd.DataFrame, budget: float):
    fig = px.bar(
        ranked, x="within_budget_share", y="neighbourhood", orientation="h", color="within_budget_share",
        color_continuous_scale=SHARE_SCALE, range_color=[0, 1],
        custom_data=["within_budget_n", "price_n"],
    )
    fig.update_traces(
        texttemplate="%{x:.0%}", textposition="outside", cliponaxis=False, textfont=dict(color=INK, size=12),
        hovertemplate=(f"<b>%{{y}}</b><br>%{{x:.0%}} of places are ${budget:,.0f}/night or less"
                       "<br>%{customdata[0]:,} of %{customdata[1]:,} places<extra></extra>"),
    )
    style_fig(fig, height=max(420, 28 * len(ranked) + 110))
    fig.update_layout(margin=dict(l=10, r=10, t=70, b=10),
                      coloraxis_colorbar=_bar_colorbar("Share within budget", tickformat=".0%"), bargap=.35)
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False)
    fig.update_xaxes(range=[0, 1.12], tickformat=".0%", tickvals=[0, .25, .5, .75, 1], tickangle=0,
                     title="Share of places within budget")
    return fig


def _segment_evidence(tables, filters, set_detail) -> None:
    # Selected segments carry no budget columns; the pre-budget join below is
    # the only budget evidence shown, so the share never uses the filtered subset.
    table = tables["segments"].drop(columns=["within_budget_n", "within_budget_share"])
    if filters.budget_usd is not None:
        affordability = tables["affordability_segments"][
            ["neighbourhood", "room_type", "within_budget_share"]]
        table = table.merge(affordability, on=["neighbourhood", "room_type"], how="left", validate="one_to_one")
    else:
        table["within_budget_share"] = pd.NA
    search = keep("segment_search", st.text_input(
        "Search", value=kept("segment_search", ""), key="segment_search",
        placeholder="Search a neighborhood, e.g. Venice", label_visibility="collapsed"))
    visible = table
    if search.strip():
        needle = search.strip()
        visible = table.loc[
            table.neighbourhood.str.contains(needle, case=False, regex=False, na=False)
            | table.room_type.str.contains(needle, case=False, regex=False, na=False)
        ]
    coords = tables["map"][["neighbourhood", "room_type", "latitude", "longitude"]]
    visible = _with_distances(visible.merge(coords, on=["neighbourhood", "room_type"], how="left"))
    focus = st.session_state.get("detail_neighbourhood")
    # The map-selected neighborhood is pinned to the top; the rest stay cheapest first.
    visible = visible.assign(_focus=visible.neighbourhood.ne(focus)).sort_values(
        ["_focus", "median_price", "neighbourhood", "room_type"], na_position="last").reset_index(drop=True)
    visible = visible.assign(
        within_budget_pct=visible.within_budget_share.astype("Float64") * 100,
        reviewed_pct=visible.reviewed_share.astype("Float64") * 100,
        airbnb=[airbnb_search(a, r, filters.budget_usd) for a, r in zip(visible.neighbourhood, visible.room_type)],
    )
    columns = ["neighbourhood", "room_type", "listing_count", "median_price", "price_p25", "price_p75",
               "within_budget_pct", "reviewed_pct", "median_total_reviews", "mi_Downtown LA",
               "mi_Santa Monica beach", "mi_LAX airport", "airbnb"]
    if filters.budget_usd is None:
        columns.remove("within_budget_pct")
    filter_signature = repr((filters.neighbourhoods, filters.room_types, filters.trip_nights,
                             filters.budget_usd, filters.min_reviews, filters.exclude_high_prices, search))
    key = "segment_table_" + str(abs(hash(filter_signature)))
    shown = visible[columns]
    if focus:
        shown = shown.style.apply(
            lambda row: ["background-color: #FFF0F0; font-weight: 700" if row.neighbourhood == focus else ""
                         for _ in row], axis=1)
    event = st.dataframe(
        shown, hide_index=True, width="stretch", height=440,
        on_select="rerun", selection_mode="single-row", key=key,
        column_config={
            "neighbourhood": st.column_config.TextColumn("Neighborhood"),
            "room_type": st.column_config.TextColumn("Room type"),
            "listing_count": st.column_config.NumberColumn("Places", format="%d",
                                                           help="Listings matching your filters."),
            "median_price": st.column_config.NumberColumn("Typical price", format="$%.0f",
                                                          help="Median listed price per night."),
            "price_p25": st.column_config.NumberColumn("Budget end", format="$%.0f",
                                                       help="A quarter of places cost this or less (25th percentile)."),
            "price_p75": st.column_config.NumberColumn("Upper end", format="$%.0f",
                                                       help="Three quarters of places cost this or less (75th percentile)."),
            "within_budget_pct": st.column_config.NumberColumn(
                "Fits budget", format="%.0f%%",
                help="Places at or below your budget ÷ all priced places (counted before the budget filter)."),
            "reviewed_pct": st.column_config.NumberColumn("Have reviews", format="%.0f%%",
                                                          help="Share of places with at least one review."),
            "median_total_reviews": st.column_config.NumberColumn("Typical reviews", format="%.0f",
                                                                  help="Median number of guest reviews."),
            "mi_Downtown LA": st.column_config.NumberColumn("Miles to Downtown", format="%.0f mi",
                                                            help="Straight-line miles, not driving time."),
            "mi_Santa Monica beach": st.column_config.NumberColumn("Miles to beach", format="%.0f mi",
                                                                   help="Straight-line miles to Santa Monica Pier."),
            "mi_LAX airport": st.column_config.NumberColumn("Miles to LAX", format="%.0f mi",
                                                            help="Straight-line miles to LAX airport."),
            "airbnb": st.column_config.LinkColumn("Airbnb", display_text="Search ↗",
                                                  help="Opens a live Airbnb search for this neighborhood, room type "
                                                       "and budget."),
        },
    )
    rows = event.selection.rows if event is not None else []
    if rows:
        selected_area = str(visible.iloc[rows[0]].neighbourhood)
        signature = (key, selected_area)
        if st.session_state.get("last_segment_selection") != signature:
            st.session_state.last_segment_selection = signature
            set_detail(selected_area)
    st.caption("Tip: click a column header to sort. Select a row (or click a map bubble) to spotlight a neighborhood.")


def _spotlight(tables, filters, set_detail) -> None:
    """Inline drawer for the focused neighborhood: key numbers, nearest landmarks and cheapest listings."""
    area = st.session_state.get("detail_neighbourhood")
    if not area:
        return
    rows = _with_distances(tables["map"].loc[tables["map"].neighbourhood.eq(area)])
    listings = tables["listings"].loc[tables["listings"].neighbourhood.eq(area)]
    with st.container(key="panel_spotlight"):
        head, actions = st.columns([3, 1], vertical_alignment="center")
        with head:
            panel_header("Spotlight", area)
        if actions.button("Clear spotlight", key="clear_spotlight", width="stretch"):
            set_detail(None)
            st.rerun()
        if rows.empty:
            st.info(f"No places in {area} match your current filters.")
            return
        for _, row in rows.iterrows():
            cols = st.columns([1, 1, 1, 1.4], vertical_alignment="center")
            cols[0].markdown(f"**{row.room_type}**  \n{number(row.listing_count)} places")
            cols[1].markdown(f"**{usd(row.median_price)}** /night  \ntypical price")
            cols[2].markdown(f"**{number(row['mi_Downtown LA'])} mi** to Downtown  \n"
                             f"{number(row['mi_Santa Monica beach'])} mi to beach · {number(row['mi_LAX airport'])} mi to LAX")
            cols[3].link_button(f"Search {area} on Airbnb ↗", airbnb_search(area, row.room_type, filters.budget_usd),
                                width="stretch")
        cheapest = listings.dropna(subset=["price"]).sort_values(["price", "id"]).head(5)
        if not cheapest.empty:
            st.markdown("**Lowest-priced places here**")
            st.dataframe(
                cheapest.assign(link="https://www.airbnb.com/rooms/" + cheapest.id.astype("string"))[
                    ["link", "room_type", "price", "minimum_nights", "number_of_reviews"]],
                hide_index=True, width="stretch",
                column_config={
                    "link": st.column_config.LinkColumn("Airbnb", display_text="View listing ↗"),
                    "room_type": st.column_config.TextColumn("Room type"),
                    "price": st.column_config.NumberColumn("Price/night", format="$%.0f"),
                    "minimum_nights": st.column_config.NumberColumn("Min. nights", format="%d"),
                    "number_of_reviews": st.column_config.NumberColumn("Reviews", format="%d"),
                },
            )


def render_explore(tables, filters, set_detail, room_views, detail_picker) -> None:
    rooms = filters.room_types or ()
    selected_count = len(tables["listings"])

    section("Overview", "At a glance")
    if selected_count == 0:
        st.warning("No places match these filters. Try a higher budget, a different stay length, "
                   "fewer review requirements, or press Reset.")
    if not rooms:
        metric_cards(tables["overview"].iloc[0], tables["affordability"].iloc[0], filters.budget_usd)
    for room in rooms:
        if len(rooms) > 1:
            _room_chip(room)
        room_tables = room_views[room]
        metric_cards(room_tables["overview"].iloc[0], room_tables["affordability"].iloc[0], filters.budget_usd, room)

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
    section("Prices", "Where your budget goes furthest")
    for room in rooms:
        if len(rooms) > 1:
            _room_chip(room)
        ranked = ranked_by_room[room]
        price_col, share_col = st.columns(2) if filters.budget_usd is not None else (st.container(), None)
        with price_col, st.container(key=f"panel_price_{room}"):
            panel_header("Lowest typical prices", f"Most affordable neighborhoods · {room}",
                         "Median listed price per night for places matching your filters. Neighborhoods need "
                         "at least 30 priced places to be ranked. Places without a price are left out.")
            if ranked.empty:
                st.info("Not enough priced places to rank neighborhoods. Try widening your filters.")
            else:
                st.plotly_chart(_price_bars(ranked, shared_max), width="stretch", key=f"price_bars_{room}",
                                config=STATIC)
        if share_col is None:
            continue
        ranked_share = rank_market_segments(pre.loc[pre.room_type.eq(room)], metric="within_budget_share",
                                            min_n=30, ascending=False).head(15)
        with share_col, st.container(key=f"panel_share_{room}"):
            panel_header("Best budget fit", f"Most places under ${filters.budget_usd:,.0f} · {room}",
                         "Places at or below your budget ÷ all priced places in the neighborhood, counted before "
                         "the budget filter so the share is never forced to 100%.")
            if ranked_share.empty:
                st.info("Not enough priced places to rank neighborhoods by budget fit.")
            else:
                st.plotly_chart(_share_bars(ranked_share, filters.budget_usd), width="stretch",
                                key=f"affordability_bars_{room}", config=STATIC)

    cdf = tables["price_distribution"]
    cdf = cdf.loc[cdf.room_type.isin(rooms)]
    with st.container(key="panel_cdf"):
        panel_header("Price spread", "How many places cost less than a given price?",
                     "Read across from any nightly price to the share of places listed at or below it. Counted "
                     "before the budget filter. The axis stops at the 99th percentile so a handful of very "
                     "expensive listings don't squash the chart; they are still counted.")
        if cdf.empty:
            st.info("No prices are available for these filters.")
        else:
            fig = px.line(
                cdf, x="nightly_price_usd", y="cumulative_share", color="room_type", line_shape="hv",
                color_discrete_map=ROOM_COLORS, labels={"room_type": "Room type"},
            )
            fig.update_traces(line=dict(width=2),
                              hovertemplate="<b>%{fullData.name}</b><br>%{y:.0%} of places cost "
                                            "$%{x:,.0f}/night or less<extra></extra>")
            style_fig(fig, height=400)
            fig.update_yaxes(range=[0, 1.02], tickformat=".0%", title="Share of places")
            prices = cdf.loc[cdf.cumulative_share.le(.99), "nightly_price_usd"]
            x_max = usable_max(prices if not prices.empty else cdf.nightly_price_usd)
            if filters.budget_usd is not None:
                x_max = max(x_max, filters.budget_usd * 1.1)
            fig.update_xaxes(range=[0, x_max], title="Price per night", tickprefix="$")
            if filters.budget_usd is not None:
                fig.add_trace(go.Scatter(
                    x=[filters.budget_usd, filters.budget_usd], y=[0, 1], mode="lines+text",
                    line=dict(color=INK, width=1.5, dash="dash"),
                    text=[f" Your budget ${filters.budget_usd:,.0f}", ""], textposition="top right",
                    textfont=dict(color=INK, size=12), hoverinfo="skip", showlegend=False,
                ))
            fig.update_layout(legend=dict(orientation="h", y=1.08, x=0, title=None))
            st.plotly_chart(fig, width="stretch", key="price_cdf", config=STATIC)

    section("Map", "Neighborhoods across Los Angeles",
            "Each bubble sits at the average location of a neighborhood's listings (not an official boundary). "
            "Bubble size = number of places. Click a bubble to spotlight that neighborhood in the table below. "
            "Distances are straight-line miles, not driving or transit time.")
    with st.container(key="panel_map"):
        controls = st.columns(2, vertical_alignment="bottom")
        metric_options = ["Typical price per night", "Fits your budget"]
        metric = keep("map_metric", controls[0].selectbox(
            "Color bubbles by", metric_options, key="map_metric",
            index=metric_options.index(kept("map_metric", metric_options[0]))))
        with controls[1]:
            detail_picker()
        share_map = metric == "Fits your budget"
        if share_map and filters.budget_usd is None:
            st.info("Pick a nightly budget in the filters above to color neighborhoods by budget fit.")
        else:
            source = tables["affordability_map"] if share_map else tables["map"]
            color_column = "within_budget_share" if share_map else "median_price"
            color_title = "Fits budget" if share_map else "Typical price"
            for room in rooms:
                if len(rooms) > 1:
                    _room_chip(room)
                result = _map_fig(source.loc[source.room_type.eq(room)], color_column, color_title, share_map,
                                  st.session_state.get("detail_neighbourhood"))
                if result is None:
                    st.info(f"No neighborhoods to map for {room} under these filters.")
                    continue
                fig, bounds = result
                map_col, locator_col = st.columns([3, 1])
                key = f"neighborhood_map_{room}_{'budget' if share_map else 'price'}"
                with map_col:
                    st.plotly_chart(fig, width="stretch", key=key, on_select="rerun", selection_mode="points",
                                    config={"displaylogo": False, "scrollZoom": True,
                                            "modeBarButtonsToRemove": ["lasso2d", "select2d", "toImage"]})
                    _detail_from_plotly(key, set_detail)
                with locator_col:
                    st.markdown('<div class="panel-kicker">Where you are</div>', unsafe_allow_html=True)
                    st.plotly_chart(_usa_locator(bounds), width="stretch", key=f"usa_locator_{room}",
                                    config=STATIC)
                    st.markdown('<p class="map-legend-note">The coral dot marks Los Angeles, the area shown on the street map. '
                                'Bigger bubbles mean more places; darker color means '
                                + ("more places fit your budget." if share_map else "a higher typical price.")
                                + '</p>', unsafe_allow_html=True)
            st.caption("Map tiles © OpenStreetMap contributors © CARTO.")

    section("All neighborhoods", "Compare every neighborhood")
    with st.container(key="panel_segments"):
        _segment_evidence(tables, filters, set_detail)
    _spotlight(tables, filters, set_detail)
