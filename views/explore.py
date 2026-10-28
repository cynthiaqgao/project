from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from phase2.backend import rank_market_segments
from .common import add_small_metric_flags, metric_cards, number, pct, usable_max


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


def _map_fig(frame: pd.DataFrame, room: str, color_column: str, color_title: str,
             is_share: bool, online: bool, population: str):
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
        marker = dict(size=part.listing_count.astype(float), sizemode="area", sizeref=sizeref,
                      color="#8d99a6" if missing else part[color_column].astype(float))
        if not missing:
            marker.update(colorscale="Viridis", cmin=0, cmax=value_max,
                          colorbar=dict(title=color_title, tickformat=".0%" if is_share else "$,.0f"))
        trace_args = dict(
            mode="markers", marker=marker, customdata=part._custom.tolist(),
            name="Missing metric" if missing else room,
            hovertemplate=(
                "Neighborhood: %{customdata[0]}<br>Room type: %{customdata[1]}<br>"
                "Listings in map population: %{customdata[2]}<br>Valid coordinates (map_n): %{customdata[3]}<br>"
                "Selected price_n: %{customdata[4]}<br>Selected median USD/night: %{customdata[5]}<br>"
                "Selected missing prices: %{customdata[6]}<br>Pre-budget within-budget count: %{customdata[7]}<br>"
                "Pre-budget within-budget share: %{customdata[8]:.1%}<br>"
                "Pre-budget price_n denominator: %{customdata[9]}<extra></extra>"
            ),
        )
        if online:
            fig.add_trace(go.Scattermap(
                lat=part.latitude.astype(float), lon=part.longitude.astype(float), **trace_args
            ))
        else:
            fig.add_trace(go.Scatter(
                x=part.longitude.astype(float), y=part.latitude.astype(float), **trace_args
            ))
    for count in legend_counts:
        marker = dict(size=count, sizemode="area", sizeref=sizeref,
                      color="#778391", line=dict(color="#526274", width=1))
        if online:
            fig.add_trace(go.Scattermap(lat=[None], lon=[None], mode="markers", marker=marker,
                                        name=f"{count:,} listings"))
        else:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=marker,
                                     name=f"{count:,} listings"))
    fig.update_layout(
        title=f"{color_title} · {room} · {population}", height=500,
        margin=dict(l=20, r=20, t=65, b=70),
        legend=dict(orientation="h", y=-0.18, title="Marker area ∝ listing count"),
        clickmode="event+select", dragmode="pan", paper_bgcolor="white", plot_bgcolor="white",
    )
    if online:
        lat_min, lat_max = float(valid.latitude.min()), float(valid.latitude.max())
        lon_min, lon_max = float(valid.longitude.min()), float(valid.longitude.max())
        center_lat, center_lon = (lat_min + lat_max) / 2, (lon_min + lon_max) / 2
        span = max(lat_max - lat_min, lon_max - lon_min, 0.01)
        zoom = max(4, min(11, math.log2(360 / span) - 1))
        fig.update_layout(map=dict(style="open-street-map", center=dict(lat=center_lat, lon=center_lon), zoom=zoom))
    else:
        fig.update_xaxes(title="Longitude (degrees)", showgrid=True, zeroline=False)
        fig.update_yaxes(title="Latitude (degrees)", showgrid=True, zeroline=False,
                         scaleanchor="x", scaleratio=1 / math.cos(math.radians(34)))
    return fig


def _segment_evidence(tables, filters, set_detail) -> None:
    selected = tables["segments"].copy()
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
    search = st.text_input("Search neighborhood or room type", key="segment_search")
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
    st.caption("Budget columns are pre-budget: the numerator and denominator are computed before budget filtering. Small n<30 flags are display guidance, not statistical significance.")
    detail = st.session_state.get("detail_neighbourhood")
    styled = visible.style.apply(
        lambda row: ["background-color: #e1f3eb" if row.neighbourhood == detail else "" for _ in row], axis=1
    )
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
    st.caption("Select a segment row to set the detail neighborhood. Availability is source calendar context, not occupancy or trip confirmation.")


def render_explore(tables, filters, set_detail, room_views) -> None:
    selected_count = len(tables["listings"])
    if selected_count == 0:
        st.warning("No listings match these filters. Use Reset in the sidebar.")
    if not filters.room_types:
        st.info("Select at least one room type to show separate room-type summaries.")
    st.caption("Ranking bars require the relevant observed sample size to be at least 30. This is a display rule, not statistical significance.")

    for room in filters.room_types or ():
        room_tables = room_views[room]
        overview = room_tables["overview"].iloc[0]
        affordability = room_tables["affordability"].iloc[0]
        st.subheader(f"{room} · selected listing KPIs")
        metric_cards(st.columns(4), overview, affordability, room, filters.budget_usd)
        st.caption(
            f"Selected price_n={number(overview.price_n)}; missing selected prices={number(overview.missing_price_n)}. "
            + (f"Pre-budget affordability: {number(affordability.within_budget_n)} / {number(affordability.price_n)} observed prices. "
               if filters.budget_usd is not None else f"Budget not set; {number(affordability.price_n)} observed prices are the available pre-budget denominator. ")
            + f"Reviewed share denominator: {number(overview.listing_count)} selected listings; observed total reviews n={number(overview.review_n)}."
        )

    selected = tables["segments"]
    pre = tables["affordability_segments"]
    shared_max = usable_max(selected.median_price)
    for room in filters.room_types or ():
        part = selected.loc[selected.room_type.eq(room)]
        ranked = rank_market_segments(part, metric="median_price", min_n=30, ascending=True).head(15)
        st.subheader(f"Neighborhood prices · {room}")
        if ranked.empty:
            st.info(f"No neighborhood price medians meet price_n ≥30 for {room}.")
        else:
            fig = px.bar(
                ranked, x="median_price", y="neighbourhood", orientation="h", color="median_price",
                color_continuous_scale="Viridis", range_color=[0, shared_max],
                hover_data={"price_p25": ":$.0f", "price_p75": ":$.0f", "listing_count": True,
                            "price_n": True, "missing_price_n": True},
                labels={"median_price": "Median listed USD/night", "neighbourhood": "Neighborhood"},
                title=f"Lowest 15 neighborhood medians · selected listings · {room}",
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_xaxes(range=[0, shared_max], title="Median listed price (USD/night)")
            fig.update_layout(height=max(390, 30 * len(ranked)), margin=dict(l=20, r=25),
                              coloraxis_colorbar_title="USD/night")
            st.plotly_chart(fig, width="stretch", key=f"price_bars_{room}")
        missing = int(part.missing_price_n.sum()) if not part.empty else 0
        st.caption(f"Selected population: {number(part.listing_count.sum())} listings; {missing:,} missing prices are not included in price statistics. Price_n≥30 is the ranking display rule.")

        if filters.budget_usd is not None:
            pre_part = pre.loc[pre.room_type.eq(room)]
            ranked_affordability = rank_market_segments(
                pre_part, metric="within_budget_share", min_n=30, ascending=False
            ).head(15)
            st.subheader(f"Within-budget inventory · {room}")
            if ranked_affordability.empty:
                st.info(f"No neighborhood budget shares meet pre-budget price_n ≥30 for {room}.")
            else:
                fig = px.bar(
                    ranked_affordability, x="within_budget_share", y="neighbourhood", orientation="h",
                    color="within_budget_share", color_continuous_scale="Viridis", range_color=[0, 1],
                    hover_data={"within_budget_n": True, "price_n": True, "listing_count": True,
                                "missing_price_n": True},
                    labels={"within_budget_share": "Within-budget share", "neighbourhood": "Neighborhood"},
                    title=f"Top 15 within ${filters.budget_usd:,.0f}/night · pre-budget population · {room}",
                )
                fig.update_yaxes(autorange="reversed")
                fig.update_xaxes(range=[0, 1], tickformat=".0%", title="Share of observed pre-budget prices")
                fig.update_layout(height=max(390, 30 * len(ranked_affordability)), margin=dict(l=20, r=25),
                                  coloraxis_colorbar_title="Within budget", coloraxis_colorbar_tickformat=".0%")
                st.plotly_chart(fig, width="stretch", key=f"affordability_bars_{room}")
                st.caption("Numerator = observed prices at or below budget; denominator = all observed prices before budget filtering.")

    st.subheader("Price distribution · pre-budget priced listings")
    cdf = tables["price_distribution"]
    cdf = cdf.loc[cdf.room_type.isin(filters.room_types or ())]
    if cdf.empty:
        st.info("No observed prices are available for the selected pre-budget population; no cumulative distribution can be shown.")
    else:
        log_x = st.checkbox("Logarithmic price axis (USD/night)", value=False, key="cdf_log_x")
        fig = px.line(
            cdf, x="nightly_price_usd", y="cumulative_share", color="room_type", line_shape="hv",
            hover_data={"listing_count_at_price": True, "price_n": True},
            labels={"nightly_price_usd": "Listed price (USD/night)", "cumulative_share": "Cumulative share of priced listings", "room_type": "Room type"},
            title="Price distribution, not a time trend · pre-budget population",
        )
        fig.update_yaxes(range=[0, 1], tickformat=".0%", title="Cumulative share (0–100%)")
        if log_x:
            fig.update_xaxes(type="log", title="Listed price (USD/night, logarithmic scale)")
        else:
            fig.update_xaxes(range=[0, usable_max(cdf.nightly_price_usd)], title="Listed price (USD/night)")
        if filters.budget_usd is not None:
            fig.add_vline(x=filters.budget_usd, line_dash="dash", annotation_text="Nightly budget")
        fig.update_layout(height=430, margin=dict(l=20, r=20), legend_title="Room type")
        st.plotly_chart(fig, width="stretch", key="price_cdf")
        for room in filters.room_types or ():
            room_rows = cdf.loc[cdf.room_type.eq(room)]
            if not room_rows.empty:
                price_n = int(room_rows.price_n.iloc[0])
                room_segments = tables["affordability_segments"].loc[
                    tables["affordability_segments"].room_type.eq(room)
                ]
                pre_budget_listings = int(room_segments.listing_count.sum())
                st.caption(f"{room}: {price_n:,} observed prices in the pre-budget distribution; {pre_budget_listings - price_n:,} listings have missing prices.")

    st.subheader("Geographic overview · approximate neighborhood centers")
    map_columns = st.columns([2, 1])
    metric = map_columns[0].selectbox(
        "Map metric", ["Median listed USD/night", "Within-budget share · pre-budget"], key="map_metric"
    )
    share_map = metric.startswith("Within-budget")
    online = map_columns[1].checkbox("Online basemap", value=False, key="online_basemap")
    if share_map and filters.budget_usd is None:
        st.info("Set a nightly budget to show within-budget map colors.")
    else:
        source = tables["affordability_map"] if share_map else tables["map"]
        color_column = "within_budget_share" if share_map else "median_price"
        color_title = "Within-budget share" if share_map else "Median listed USD/night"
        population = "pre-budget" if share_map else "selected"
        for room in filters.room_types or ():
            groups = source.loc[source.room_type.eq(room)]
            valid_n = int(groups.map_n.fillna(0).sum()) if not groups.empty else 0
            total_n = int(groups.listing_count.sum()) if not groups.empty else 0
            st.caption(f"{room} · {population} marker population · {total_n - valid_n:,} listings omitted from approximate centers because coordinates did not pass the map screen.")
            if not groups.empty and groups.price_n.lt(30).any():
                st.warning(f"{room}: {int(groups.price_n.lt(30).sum())} groups have price_n <30; map markers remain visible with their sample sizes.")
            fig = _map_fig(groups, room, color_column, color_title, share_map, online, population)
            if fig is None:
                st.info(f"No mappable neighborhood centers for {room} under these filters.")
                continue
            key = f"neighborhood_map_{room}_{'budget' if share_map else 'price'}"
            st.plotly_chart(
                fig, width="stretch", key=key, on_select="rerun", selection_mode="points",
            )
            _detail_from_plotly(key, set_detail)
            if online:
                st.caption("Online OpenStreetMap basemap. Marker centers are approximate means, not listing pins, official boundaries, or density.")
            else:
                st.caption("Offline coordinate grid; axes are degrees. Marker centers are approximate means, not listing pins, official boundaries, or density.")

    st.subheader("Segment evidence · all selected neighborhood-room groups")
    _segment_evidence(tables, filters, set_detail)
