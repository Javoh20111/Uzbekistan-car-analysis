import pandas as pd
import streamlit as st
import time

from src.config import DATA_PATH


@st.cache_data(show_spinner="Loading car listings...")
def load_car_data():
    if not DATA_PATH.exists():
        st.error(
            "Could not find the cleaned dataset. "
            f"Expected file: `{DATA_PATH}`. "
            "For Streamlit Cloud, commit `data/Prepared/car_data_clean.csv` "
            "or change the app to load data from PostgreSQL/cloud storage."
        )
        st.stop()

    df = pd.read_csv(DATA_PATH)
    return df

def stream_data(Content):
    for word in Content.split(" "):
        yield word + " "
        time.sleep(0.01)
