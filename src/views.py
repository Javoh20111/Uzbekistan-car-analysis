import altair as alt
import streamlit as st


def render_dashboard(df):
    st.subheader("Market Overview")

    total_listings = len(df)
    median_price = df["price_usd"].median()
    average_price = df["price_usd"].mean()
    top_brand = df["brand"].mode().iat[0] if not df["brand"].mode().empty else "Unknown"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Listings", f"{total_listings:,}")
    col2.metric("Median Price", f"${median_price:,.0f}")
    col3.metric("Average Price", f"${average_price:,.0f}")
    col4.metric("Top Brand", top_brand)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### Listings by Brand")
        brand_counts = df["brand"].value_counts().head(15).reset_index()
        brand_counts.columns = ["brand", "listings"]
        chart = (
            alt.Chart(brand_counts)
            .mark_bar()
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
            df.groupby("region", as_index=False)["price_usd"]
            .median()
            .sort_values("price_usd", ascending=False)
            .head(15)
        )
        chart = (
            alt.Chart(region_prices)
            .mark_bar()
            .encode(
                x=alt.X("price_usd:Q", title="Median price, USD"),
                y=alt.Y("region:N", sort="-x", title="Region"),
                tooltip=["region", alt.Tooltip("price_usd:Q", format=",.0f")],
            )
        )
        st.altair_chart(chart, use_container_width=True)


def render_analysis(df):
    st.subheader("Exploratory Analysis")

    with st.sidebar:
        st.header("Filters")
        selected_brands = st.multiselect(
            "Brand",
            sorted(df["brand"].dropna().unique()),
            default=[],
        )
        selected_regions = st.multiselect(
            "Region",
            sorted(df["region"].dropna().unique()),
            default=[],
        )
        min_year = int(df["year"].dropna().min())
        max_year = int(df["year"].dropna().max())
        year_range = st.slider("Year", min_year, max_year, (min_year, max_year))

    filtered = df.copy()
    if selected_brands:
        filtered = filtered[filtered["brand"].isin(selected_brands)]
    if selected_regions:
        filtered = filtered[filtered["region"].isin(selected_regions)]
    filtered = filtered[
        filtered["year"].between(year_range[0], year_range[1], inclusive="both")
    ]

    st.write(f"Filtered listings: **{len(filtered):,}**")

    if filtered.empty:
        st.warning("No listings match the selected filters.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Price vs Year")
        chart = (
            alt.Chart(filtered.sample(min(len(filtered), 5000), random_state=42))
            .mark_circle(size=24, opacity=0.35)
            .encode(
                x=alt.X("year:Q", title="Year"),
                y=alt.Y("price_usd:Q", title="Price, USD"),
                color=alt.Color("brand:N", legend=None),
                tooltip=["brand", "car_name", "year", "price_usd"],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    with col2:
        st.markdown("#### Price by Fuel Type")
        fuel_prices = (
            filtered.groupby("fuel_type", as_index=False)["price_usd"]
            .median()
            .sort_values("price_usd", ascending=False)
        )
        chart = (
            alt.Chart(fuel_prices)
            .mark_bar()
            .encode(
                x=alt.X("price_usd:Q", title="Median price, USD"),
                y=alt.Y("fuel_type:N", sort="-x", title="Fuel type"),
                tooltip=["fuel_type", alt.Tooltip("price_usd:Q", format=",.0f")],
            )
        )
        st.altair_chart(chart, use_container_width=True)


def render_predictor(df):
    st.subheader("Price Predictor")
    st.info("Model training is not connected yet. This form is ready for the next step.")

    col1, col2 = st.columns(2)

    with col1:
        st.selectbox("Brand", sorted(df["brand"].dropna().unique()))
        st.number_input("Year", min_value=1970, max_value=2030, value=2020)
        st.number_input("Mileage", min_value=0, value=50_000, step=1_000)
        st.number_input("Engine volume", min_value=0.0, value=1.6, step=0.1)

    with col2:
        st.selectbox("Fuel type", sorted(df["fuel_type"].dropna().unique()))
        st.selectbox("Transmission", sorted(df["transmission"].dropna().unique()))
        st.selectbox("Condition", sorted(df["condition"].dropna().unique()))
        st.selectbox("Region", sorted(df["region"].dropna().unique()))

    st.button("Predict Price", disabled=True)
