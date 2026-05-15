import time
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


'''
# Uzbekistan Car Market OLX Analysis & Car predictor


'''

df = pd.read_csv('data/Prepared/car_data_clean.csv')

_LOREM_IPSUM ="Here is nearly cleaned dataset you can use it if you wish!"


def stream_data():
    for word in _LOREM_IPSUM.split(" "):
        yield word + " "
        time.sleep(0.06)

    yield pd.DataFrame(df)


if st.button("Stream data"):
    st.write_stream(stream_data)

numerical_features = ['price_usd', 'year', 'mileage', 'engine_volume_l', 'owners_count']
df_subset = df[numerical_features]

corr_matrix = df_subset.corr()

fig, ax = plt.subplots(figsize=(10, 8))

sns.heatmap(
    corr_matrix,
    annot=True,
    cmap='coolwarm',
    fmt=".2f",
    ax=ax
)

ax.set_title('Correlation Heatmap of Vehicle Features')

st.pyplot(fig)