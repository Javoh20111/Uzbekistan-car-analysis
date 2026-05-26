import streamlit as st
import altair as alt
import duckdb
from pathlib import Path

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
    st.header("An owl")


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
