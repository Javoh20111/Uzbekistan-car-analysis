import streamlit as st
import altair as alt
import duckdb
import pandas as pd
from datetime import date
from pathlib import Path
from predictive_model import (
    CATEGORICAL_MODEL_FEATURES,
    CONDITION_ORDER,
    normalize_rare_value,
    sorted_options,
    train_price_model,
)

st.set_page_config(
    page_title="Uzbekistan Car Market",
    layout="wide",
)

#---------------------------------------------------------------------
#   Data load                                                         |
#---------------------------------------------------------------------
DB_PATH = Path(__file__).parent / "cars.duckdb"


@st.cache_data(ttl=600)
def query(sql):
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return conn.execute(sql).df()
    finally:
        conn.close()


df = query("SELECT * FROM car_listings;")

model_df = query("""
    SELECT
        b.brand_name AS brand,
        c.model_clean,
        c.year,
        c.engine_volume_l,
        cl.price_usd,
        cl.mileage,
        cl.owners_count,
        cond.condition_name AS condition,
        col.color_name AS color,
        tr.transmission_name AS transmission,
        ft.fuel_type_name AS fuel_type,
        r.region_name AS region,
        d.district_name AS district
    FROM car_listings cl
    LEFT JOIN cars c
        ON cl.url = c.url
    LEFT JOIN brands b
        ON c.brand_id = b.brand_id
    LEFT JOIN conditions cond
        ON cl.condition_id = cond.condition_id
    LEFT JOIN colors col
        ON cl.color_id = col.color_id
    LEFT JOIN transmissions tr
        ON cl.transmission_id = tr.transmission_id
    LEFT JOIN fuel_types ft
        ON cl.fuel_type_id = ft.fuel_type_id
    LEFT JOIN regions r
        ON cl.region_id = r.region_id
    LEFT JOIN districts d
        ON cl.district_id = d.district_id
    WHERE
        cl.price_usd IS NOT NULL
        AND c.year IS NOT NULL
        AND c.year_valid = TRUE
        AND cl.is_outlier = FALSE
""")


#---------------------------------------------------------------------
#   Header                                                           |
#---------------------------------------------------------------------
st.write("# Uzbekistan car analysis")
st.caption("OLX car listings dashboard, exploratory analysis, and price prediction workspace.")










#---------------------------------------------------------------------
#   Sidebar                                                          |
#---------------------------------------------------------------------
with st.sidebar:
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()














#---------------------------------------------------------------------
#  Tabs                                                              |
#---------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Dashbords", "Analysis", "Predictive model", "Data"])

with tab1:
    st.subheader("Market Overview")

    #---------------------------------------------------------------------
    #  Dashboards                                                         |
    #---------------------------------------------------------------------
    total_listings = len(df)
    median_price = df["price_usd"].median()
    average_price = df["price_usd"].mean()
    top_brand = query("""
        SELECT
            brands.brand_name,
            COUNT(cars.brand_id) AS listings
        FROM
            car_listings cl
            LEFT JOIN cars on cars.url = cl.url
            LEFT JOIN brands on cars.brand_id = brands.brand_id
        GROUP BY
            brands.brand_name
        HAVING COUNT(cars.brand_id) > 0
        ORDER BY
            listings DESC
                    """)
    top_brand_name = top_brand["brand_name"].iat[0]
    top_brand_count = top_brand["listings"].iat[0]
    
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Listings", f"{total_listings:,}")
    col2.metric("Median Price", f"{median_price:,.0f}")
    col3.metric("Average Price", f"{average_price:,.0f}")
    col4.metric("Top Brands", f"{top_brand_name} ({top_brand_count:,.0f})")

    column1, column2 = st.columns(2)

    with column1:
        st.markdown("#### Listings by Brand")
        
        chart = (
            alt.Chart(top_brand)
            .mark_bar()
            .encode(
                x=alt.X("listings:Q", title="Listings"),
                y=alt.Y("brand_name:N", sort="-x", title="Brand"),
                tooltip=["brand_name", "listings"],
            )
         )
        st.altair_chart(chart, use_container_width=True)

    
    with column2:
        st.markdown("#### Median Price by Region")

        region_prices = query("""
            SELECT
                regions.region_name AS region,
                median(price_usd) AS median_price
            FROM
                car_listings cl
                LEFT JOIN regions on regions.region_id = cl.region_id
            WHERE regions.region_name IS NOT NULL
            GROUP BY
                regions.region_name
            ORDER BY
                median_price DESC;
        """)

        chart = (
            alt.Chart(region_prices)
            .mark_bar()
            .encode(
                x=alt.X("median_price:Q", title="Median price, USD"),
                y=alt.Y("region:N", sort="-x", title="Region"),
                tooltip=["region", alt.Tooltip("median_price:Q", format=",.0f")],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    car_age, = st.columns(1)

    with car_age:
        st.markdown("#### Distribution of Car Manufacturing Years")

        car_years = query("""
            SELECT
                year
            FROM
                cars
            WHERE
                year_valid = TRUE
                AND year IS NOT NULL
                AND year > 1950
        """)

        chart = (
            alt.Chart(car_years)
            .mark_bar()
            .encode(
                x=alt.X(
                    "year:O",
                    title="Manufacturing Year",
                    sort="ascending"
                ),
                y=alt.Y(
                    "count():Q",
                    title="Number of Listings"
                ),
                tooltip=[
                    alt.Tooltip("year:O", title="Year"),
                    alt.Tooltip("count():Q", title="Listings")
                ]
            )
            .properties(height=400)
        )

        st.altair_chart(chart, use_container_width=True)






with tab2:
    st.header("Charts & Insights")



with tab3:
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
                    max_value = date.today().year + 1,
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
                condition = st.selectbox("Condition", list(CONDITION_ORDER.keys()), index=2)
                region = st.selectbox("Region", sorted_options(df, "region"))
                district = st.selectbox("District", sorted_options(df, "district"))
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

    render_predictor(model_df)




with tab4:
    #---------------------------------------------------------------------
    #  Clean dataset                                                      |
    #---------------------------------------------------------------------
    st.subheader("Cleaned Dataset")

    cleaned_df = query("""
    SELECT
        cl.url,
        c.car_name,
        b.brand_name,
        c.model_clean,
        c.year,
        c.year_valid,
        c.engine_volume_l,

        cl.description,
        cl.price_usd,
        cl.is_outlier,

        cond.condition_name,
        col.color_name,
        tr.transmission_name,
        ft.fuel_type_name,

        r.region_name,
        d.district_name,

        cl.mileage,
        cl.mileage_log,
        cl.mileage_group,

        cl.owners_count,
        cl.created_at,
        cl.image_url

    FROM car_listings cl

    LEFT JOIN cars c
        ON cl.url = c.url

    LEFT JOIN brands b
        ON c.brand_id = b.brand_id

    LEFT JOIN currencies curr
        ON cl.currency_id = curr.currency_id

    LEFT JOIN conditions cond
        ON cl.condition_id = cond.condition_id

    LEFT JOIN colors col
        ON cl.color_id = col.color_id

    LEFT JOIN transmissions tr
        ON cl.transmission_id = tr.transmission_id

    LEFT JOIN fuel_types ft
        ON cl.fuel_type_id = ft.fuel_type_id

    LEFT JOIN regions r
        ON cl.region_id = r.region_id

    LEFT JOIN districts d
        ON cl.district_id = d.district_id

    WHERE 
        cl.is_outlier IS NOT NULL
        AND cl.region_id IS NOT NULL
        AND cl.district_id IS NOT NULL
        AND cl.owners_count IS NOT NULL
        AND cond.condition_name IS NOT NULL
        AND col.color_name IS NOT NULL
        AND tr.transmission_name IS NOT NULL
        """)
    csv = cleaned_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download cleaned CSV",
        data=csv,
        file_name="car_postings_olx.csv",
        mime="text/csv",
    )
    st.dataframe(cleaned_df, use_container_width=True)

    st.subheader("Want to build project like this!!? I’ve got you.")
    st.markdown("Visit the [datasets/shukrullo](https://www.kaggle.com/datasets/shukrullo/all-car-ads-from-olx-as-scraped) to take raw data.", unsafe_allow_html=True)
