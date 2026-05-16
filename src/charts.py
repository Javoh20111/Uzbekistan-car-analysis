import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import numpy as np

from src.config import NUMERIC_FEATURES

def render_boxplot(df):
    sns.set_style("darkgrid", {"grid.color": ".6", "grid.linestyle": ":"})
    price = df.loc[df['price_usd'].notna(), 'price_usd']
    fig, axes = plt.subplots(figsize=(7, 4))
    ax1 = axes
    ax1.boxplot(price, vert=False,patch_artist=True, boxprops=dict(facecolor="steelblue", alpha=0.6))
    ax1.set_title('Price USD boxplot')
    ax1.set_xlabel("Price USD")
    st.pyplot(fig)


def render_hist(df):
    plt.figure(figsize=(10, 4))
    sns.set_style("darkgrid", {"grid.color": ".6", "grid.linestyle": ":"})

    data = df[df['year_valid']]['year']
    bins = np.arange(data.min(), data.max() + 1, 1)
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.hist(df[df['year_valid']]['year'], bins=bins)
    plt.title("Distribution of Car Manufacturing Years (Valid Data Only)")
    plt.xlabel("Manufacturing Year")
    plt.ylabel("Number of Listings")
    st.pyplot(fig)

def render_correlation_heatmap(df):
    st.subheader("Correlation Heatmap")

    available_features = [column for column in NUMERIC_FEATURES if column in df.columns]
    corr_matrix = df[available_features].corr(numeric_only=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", fmt=".2f", ax=ax)
    ax.set_title("Correlation Heatmap of Vehicle Features")

    st.pyplot(fig)




