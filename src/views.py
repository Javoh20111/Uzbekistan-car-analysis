import altair as alt
import pandas as pd
import streamlit as st
from datetime import date

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NUMERIC_MODEL_FEATURES = [
    "mileage",
    "engine_volume_l",
    "owners_count",
    "age",
    "condition",
]

CATEGORICAL_MODEL_FEATURES = [
    "brand",
    "model_clean",
    "fuel_type",
    "transmission",
    "body_type",
    "region",
    "color",
    "district",
]

CONDITION_ORDER = {
    "Needs Repair": 0,
    "Average": 1,
    "Good": 2,
    "Excellent": 3,
}


def group_rare_values(series, min_count=100):
    counts = series.value_counts()
    common_values = counts[counts >= min_count].index
    return series.where(series.isin(common_values), "Other"), set(common_values)


def prepare_model_data(df):
    model_df = df.copy()

    if "district" not in model_df.columns and "district_clean" in model_df.columns:
        model_df["district"] = model_df["district_clean"]

    if "age" not in model_df.columns:
        model_df["age"] = date.today().year - model_df["year"]

    model_df["condition"] = model_df["condition"].map(CONDITION_ORDER)
    model_df = model_df[
        (model_df["age"].between(0, 45)) &
        (model_df["price_usd"].between(500, 100000))
    ].copy()

    required_columns = NUMERIC_MODEL_FEATURES + CATEGORICAL_MODEL_FEATURES + ["price_usd"]
    model_df = model_df.dropna(subset=["price_usd"])
    model_df = model_df[required_columns]
    model_df[NUMERIC_MODEL_FEATURES] = model_df[NUMERIC_MODEL_FEATURES].apply(
        pd.to_numeric,
        errors="coerce",
    )
    model_df[CATEGORICAL_MODEL_FEATURES] = model_df[CATEGORICAL_MODEL_FEATURES].astype(str)

    rare_value_maps = {}
    for column in ["model_clean", "district"]:
        model_df[column], common_values = group_rare_values(model_df[column], min_count=100)
        rare_value_maps[column] = common_values

    return model_df, rare_value_maps


@st.cache_resource(show_spinner="Training price prediction model...")
def train_price_model(df):
    model_df, rare_value_maps = prepare_model_data(df)

    X = model_df[NUMERIC_MODEL_FEATURES + CATEGORICAL_MODEL_FEATURES]
    y = model_df["price_usd"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    try:
        one_hot_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:
        one_hot_encoder = OneHotEncoder(handle_unknown="ignore", sparse=True)

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", one_hot_encoder),
    ])

    preprocessor = ColumnTransformer(transformers=[
        ("num", numeric_transformer, NUMERIC_MODEL_FEATURES),
        ("cat", categorical_transformer, CATEGORICAL_MODEL_FEATURES),
    ])

    model = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(
            n_estimators=120,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )),
    ])

    model.fit(X_train, y_train)
    test_predictions = model.predict(X_test)

    metrics = {
        "mae": mean_absolute_error(y_test, test_predictions),
        "rmse": mean_squared_error(y_test, test_predictions) ** 0.5,
        "r2": r2_score(y_test, test_predictions),
        "training_rows": len(X_train),
        "testing_rows": len(X_test),
    }

    return model, metrics, rare_value_maps


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
    model, metrics, rare_value_maps = train_price_model(df)

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Model", "Random Forest")
    metric_col2.metric("Test RMSE", f"${metrics['rmse']:,.0f}")
    metric_col3.metric("Test R2", f"{metrics['r2']:.3f}")

    st.caption(
        f"Trained on {metrics['training_rows']:,} listings and tested on "
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
