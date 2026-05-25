from datetime import date

import altair as alt
import pandas as pd
import streamlit as st


PRICE_COLUMN = "price_usd"


def _format_usd(value):
    if pd.isna(value):
        return "-"
    return f"${value:,.0f}"


def _options(df, column):
    if column not in df.columns:
        return []
    return sorted(df[column].dropna().astype(str).unique())


def _filtered_data(df):
    with st.sidebar:
        st.header("Filters")
        brands = st.multiselect("Brand", _options(df, "brand"))
        regions = st.multiselect("Region", _options(df, "region"))
        body_types = st.multiselect("Body type", _options(df, "body_type"))

        year_values = pd.to_numeric(df["year"], errors="coerce").dropna()
        min_year = int(year_values.min())
        max_year = int(year_values.max())
        year_range = st.slider("Year", min_year, max_year, (min_year, max_year))

        price_values = pd.to_numeric(df[PRICE_COLUMN], errors="coerce").dropna()
        min_price = int(price_values.min())
        max_price = int(price_values.quantile(0.99))
        price_range = st.slider(
            "Price, USD",
            min_price,
            max_price,
            (min_price, max_price),
            step=500,
        )

    filtered = df.copy()
    if brands:
        filtered = filtered[filtered["brand"].astype(str).isin(brands)]
    if regions:
        filtered = filtered[filtered["region"].astype(str).isin(regions)]
    if body_types:
        filtered = filtered[filtered["body_type"].astype(str).isin(body_types)]

    filtered = filtered[
        pd.to_numeric(filtered["year"], errors="coerce").between(*year_range)
        & pd.to_numeric(filtered[PRICE_COLUMN], errors="coerce").between(*price_range)
    ]
    return filtered


def render_dashboard(df):
    st.subheader("Market Overview")

    price = pd.to_numeric(df[PRICE_COLUMN], errors="coerce")
    total_listings = len(df)
    median_price = price.median()
    average_price = price.mean()
    top_brand = df["brand"].mode().iat[0] if not df["brand"].mode().empty else "Unknown"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Listings", f"{total_listings:,}")
    col2.metric("Median Price", _format_usd(median_price))
    col3.metric("Average Price", _format_usd(average_price))
    col4.metric("Top Brand", top_brand)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### Listings by Brand")
        brand_counts = df["brand"].value_counts().head(15).reset_index()
        brand_counts.columns = ["brand", "listings"]
        chart = (
            alt.Chart(brand_counts)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X("listings:Q", title="Listings"),
                y=alt.Y("brand:N", sort="-x", title="Brand"),
                tooltip=["brand", "listings"],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    with chart_col2:
        st.markdown("#### Median Price by Region")
        region_prices = (
            df.groupby("region", as_index=False)[PRICE_COLUMN]
            .median()
            .sort_values(PRICE_COLUMN, ascending=False)
            .head(15)
        )
        chart = (
            alt.Chart(region_prices)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X(f"{PRICE_COLUMN}:Q", title="Median price, USD"),
                y=alt.Y("region:N", sort="-x", title="Region"),
                tooltip=["region", alt.Tooltip(f"{PRICE_COLUMN}:Q", format=",.0f")],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    st.markdown("#### Price Distribution")
    hist_df = df[[PRICE_COLUMN]].dropna()
    chart = (
        alt.Chart(hist_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{PRICE_COLUMN}:Q", bin=alt.Bin(maxbins=50), title="Price, USD"),
            y=alt.Y("count():Q", title="Listings"),
            tooltip=[alt.Tooltip("count():Q", title="Listings")],
        )
    )
    st.altair_chart(chart, use_container_width=True)


def render_analysis(df):
    st.subheader("Exploratory Analysis")

    filtered = _filtered_data(df)
    st.write(f"Filtered listings: **{len(filtered):,}**")

    if filtered.empty:
        st.warning("No listings match the selected filters.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Price vs Year")
        sample = filtered.sample(min(len(filtered), 5000), random_state=42)
        chart = (
            alt.Chart(sample)
            .mark_circle(size=24, opacity=0.35)
            .encode(
                x=alt.X("year:Q", title="Year"),
                y=alt.Y(f"{PRICE_COLUMN}:Q", title="Price, USD"),
                color=alt.Color("brand:N", legend=None),
                tooltip=["brand", "car_name", "year", PRICE_COLUMN, "mileage"],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    with col2:
        st.markdown("#### Median Price by Fuel Type")
        fuel_prices = (
            filtered.groupby("fuel_type", as_index=False)[PRICE_COLUMN]
            .median()
            .sort_values(PRICE_COLUMN, ascending=False)
        )
        chart = (
            alt.Chart(fuel_prices)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X(f"{PRICE_COLUMN}:Q", title="Median price, USD"),
                y=alt.Y("fuel_type:N", sort="-x", title="Fuel type"),
                tooltip=["fuel_type", alt.Tooltip(f"{PRICE_COLUMN}:Q", format=",.0f")],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    st.markdown("#### Body Type Share")
    body_counts = filtered["body_type"].value_counts().head(10).reset_index()
    body_counts.columns = ["body_type", "listings"]
    chart = (
        alt.Chart(body_counts)
        .mark_arc(innerRadius=55)
        .encode(
            theta=alt.Theta("listings:Q"),
            color=alt.Color("body_type:N", title="Body type"),
            tooltip=["body_type", "listings"],
        )
    )
    st.altair_chart(chart, use_container_width=True)


def render_price_estimator(df):
    st.subheader("Price Check")

    clean_df = df.copy()
    clean_df[PRICE_COLUMN] = pd.to_numeric(clean_df[PRICE_COLUMN], errors="coerce")
    clean_df["year"] = pd.to_numeric(clean_df["year"], errors="coerce")
    clean_df["mileage"] = pd.to_numeric(clean_df["mileage"], errors="coerce")
    clean_df = clean_df.dropna(subset=[PRICE_COLUMN, "year"])

    with st.form("price_check_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            brand = st.selectbox("Brand", _options(clean_df, "brand"))
            model = st.selectbox("Model", _options(clean_df[clean_df["brand"] == brand], "model_clean"))
            year = st.number_input(
                "Year",
                min_value=1970,
                max_value=date.today().year + 1,
                value=min(2020, date.today().year),
            )

        with col2:
            region = st.selectbox("Region", _options(clean_df, "region"))
            fuel_type = st.selectbox("Fuel type", _options(clean_df, "fuel_type"))
            transmission = st.selectbox("Transmission", _options(clean_df, "transmission"))

        with col3:
            body_type = st.selectbox("Body type", _options(clean_df, "body_type"))
            mileage = st.number_input("Mileage", min_value=0, value=50_000, step=1_000)
            year_window = st.slider("Year match window", 1, 8, 3)

        submitted = st.form_submit_button("Estimate")

    if not submitted:
        return

    comparable = clean_df[
        (clean_df["brand"] == brand)
        & (clean_df["model_clean"] == model)
        & (clean_df["year"].between(year - year_window, year + year_window))
    ]

    mileage_window = max(25_000, int(mileage * 0.5))
    mileage_matched = comparable[
        comparable["mileage"].between(mileage - mileage_window, mileage + mileage_window)
    ]
    if len(mileage_matched) >= 10:
        comparable = mileage_matched

    if len(comparable) < 10:
        comparable = clean_df[
            (clean_df["brand"] == brand)
            & (clean_df["body_type"] == body_type)
            & (clean_df["fuel_type"] == fuel_type)
            & (clean_df["transmission"] == transmission)
            & (clean_df["year"].between(year - year_window, year + year_window))
        ]

    if len(comparable) < 5:
        comparable = clean_df[
            (clean_df["brand"] == brand)
            & (clean_df["year"].between(year - year_window, year + year_window))
        ]

    if comparable.empty:
        st.warning("No comparable listings found. Try a wider year window.")
        return

    median_price = comparable[PRICE_COLUMN].median()
    low_price = comparable[PRICE_COLUMN].quantile(0.25)
    high_price = comparable[PRICE_COLUMN].quantile(0.75)

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Estimated Price", _format_usd(median_price))
    metric_col2.metric("Typical Range", f"{_format_usd(low_price)} - {_format_usd(high_price)}")
    metric_col3.metric("Comparable Listings", f"{len(comparable):,}")

    st.caption(
        "This estimate uses median prices from similar listings in the cleaned dataset, "
        "so it is stable and does not require a saved machine learning model."
    )

    preview_columns = [
        "car_name",
        "brand",
        "model_clean",
        "year",
        "mileage",
        "region",
        "fuel_type",
        "transmission",
        PRICE_COLUMN,
    ]
    available_columns = [column for column in preview_columns if column in comparable.columns]
    st.dataframe(
        comparable.sort_values(PRICE_COLUMN)[available_columns].head(100),
        use_container_width=True,
    )


def render_data_table(df):
    st.subheader("Cleaned Dataset")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download cleaned CSV",
        data=csv,
        file_name="car_postings_olx.csv",
        mime="text/csv",
    )
    st.dataframe(df, use_container_width=True)
