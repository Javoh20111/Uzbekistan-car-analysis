import pandas as pd
import streamlit as st

from src.config import DATA_PATH


@st.cache_data(show_spinner="Loading car listings...")
def load_car_data():
    df = pd.read_csv(DATA_PATH)
    return df
