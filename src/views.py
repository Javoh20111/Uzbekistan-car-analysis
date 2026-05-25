import altair as alt
import pandas as pd
import sklearn
import streamlit as st
from datetime import date

from src.config import MODEL_ARTIFACT_PATH
from src.price_model import (
    CATEGORICAL_MODEL_FEATURES,
    CONDITION_ORDER,
    load_price_model,
)


@st.cache_resource(show_spinner="Loading price prediction model...")
def load_cached_price_model(path, modified_time):
    return load_price_model(path)


def sorted_options(df, column):
    return sorted(df[column].dropna().astype(str).unique())


def normalize_rare_value(value, common_values):
    return value if value in common_values else "Other"


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

    if not MODEL_ARTIFACT_PATH.exists():
        st.warning(
            "The trained model file is missing. Run "
            "`python3 scripts/train_price_model.py` once, then restart the app."
        )
        return

    try:
        artifact = load_cached_price_model(
            str(MODEL_ARTIFACT_PATH),
            MODEL_ARTIFACT_PATH.stat().st_mtime,
        )
    except Exception as exc:
        st.error(
            "Could not load the saved price model. This usually happens when the "
            "model was trained with a different Python or scikit-learn version "
            "than the one running the app."
        )
        st.caption(f"Current scikit-learn version: {sklearn.__version__}")
        st.code("python3 scripts/train_price_model.py\npython3 -m streamlit run app.py")
        st.exception(exc)
        return
    model = artifact["model"]
    metrics = artifact["metrics"]
    rare_value_maps = artifact["rare_value_maps"]

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Model", "Random Forest")
    metric_col2.metric("Test RMSE", f"${metrics['rmse']:,.0f}")
    metric_col3.metric("Test R2", f"{metrics['r2']:.3f}")

    st.caption(
        f"Loaded saved model trained on {metrics['training_rows']:,} listings and tested on "
        f"{metrics['testing_rows']:,} listings."
    )

    with st.form("price_prediction_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            brand = st.selectbox("Brand", sorted_options(df, "brand"))
            model_clean = st.selectbox("Model", sorted_options(df, "model_clean"))
            year = st.number_input(
                "Year",
                min_value=1970,
                max_value=date.today().year + 1,
                value=min(2020, date.today().year),
            )
            mileage = st.number_input("Mileage", min_value=0, value=50_000, step=1_000)

        with col2:
            engine_volume_l = st.number_input(
                "Engine volume (L)",
                min_value=0.0,
                max_value=8.0,
                value=1.6,
                step=0.1,
            )
            owners_count = st.number_input(
                "Owners count",
                min_value=0,
                max_value=10,
                value=1,
                step=1,
            )
            fuel_type = st.selectbox("Fuel type", sorted_options(df, "fuel_type"))
            transmission = st.selectbox("Transmission", sorted_options(df, "transmission"))

        with col3:
            body_type = st.selectbox("Body type", sorted_options(df, "body_type"))
            condition = st.selectbox("Condition", list(CONDITION_ORDER.keys()), index=2)
            region = st.selectbox("Region", sorted_options(df, "region"))
            district_column = "district" if "district" in df.columns else "district_clean"
            district = st.selectbox("District", sorted_options(df, district_column))
            color = st.selectbox("Color", sorted_options(df, "color"))

        submitted = st.form_submit_button("Predict Price")

    if submitted:
        prediction_input = pd.DataFrame([{
            "mileage": mileage,
            "engine_volume_l": engine_volume_l,
            "owners_count": owners_count,
            "age": date.today().year - year,
            "condition": CONDITION_ORDER[condition],
            "brand": brand,
            "model_clean": normalize_rare_value(model_clean, rare_value_maps["model_clean"]),
            "fuel_type": fuel_type,
            "transmission": transmission,
            "body_type": body_type,
            "region": region,
            "color": color,
            "district": normalize_rare_value(district, rare_value_maps["district"]),
        }])

        prediction_input[CATEGORICAL_MODEL_FEATURES] = prediction_input[
            CATEGORICAL_MODEL_FEATURES
        ].astype(str)
        predicted_price = model.predict(prediction_input)[0]

        result_col1, result_col2 = st.columns([1, 2])
        result_col1.metric("Estimated Price", f"${predicted_price:,.0f}")
        result_col2.info(
            f"Typical model error is about ${metrics['mae']:,.0f} MAE, "
            "so treat this as a market estimate rather than an exact listing price."
        )
