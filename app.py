import streamlit as st
import altair as alt
import pandas as pd

#---------------------------------------------------------------------
#   Data load                                                         |
#---------------------------------------------------------------------
# 1. Initialize connection
# The "sql" type uses SQLAlchemy under the hood
conn = st.connection("postgresql", type="sql")

# 2. Perform a query and cache the result
df = conn.query("SELECT * FROM car_listings;", ttl=600)



st.set_page_config(
    page_title="Uzbekistan Car Market",
    layout="wide",
)


#---------------------------------------------------------------------
#   Header                                                           |
#---------------------------------------------------------------------
st.write("# Uzbekistan car analysis")
st.caption("OLX car listings dashboard, exploratory analysis, and price prediction workspace.")










#---------------------------------------------------------------------
#   Sidebar                                                          |
#---------------------------------------------------------------------
st.sidebar.write("HI")














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
    top_brand = conn.query("""
        SELECT
            brands.brand_name,
            COUNT(cars.brand_id) AS count
        FROM
            car_listings cl
            LEFT JOIN cars on cars.url = cl.url
            LEFT JOIN brands on cars.brand_id = brands.brand_id
        GROUP BY
            brands.brand_name
        HAVING COUNT(cars.brand_id) > 0
        ORDER BY
            count DESC
                    """, ttl=600)
    top_brand_name = top_brand["brand_name"].iat[0]
    top_brand_count = top_brand["count"].iat[0]
    
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Listings", f"{total_listings:,}")
    col2.metric("Median Price", f"{median_price:,.0f}")
    col3.metric("Average Price", f"{average_price:,.0f}")
    col4.metric("Top Brands", f"{top_brand_name} ({top_brand_count:,.0f})")




with tab2:
    st.header("A dog")

with tab3:
    st.header("An owl")

with tab4:
    st.subheader("Cleaned Dataset")

    cleaned_df = conn.query("""
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

    WHERE cl.is_outlier = FALSE;
        """)
    csv = cleaned_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download cleaned CSV",
        data=csv,
        file_name="car_postings_olx.csv",
        mime="text/csv",
    )
    st.dataframe(cleaned_df, use_container_width=True)