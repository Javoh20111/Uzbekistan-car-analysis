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
    if column not in df.columns:
        return []
    return sorted(df[column].dropna().astype(str).unique())


def normalize_rare_value(value, common_values):
    return value if value in common_values else "Other"





