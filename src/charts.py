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

def categorical_analysis(df):
    brand_counts = df['brand'].value_counts()

    fig, axs = plt.subplots(ncols=2, nrows=2, figsize=(13, 10), layout="constrained")
    fig.suptitle("Categorical Analysis", fontsize=15, fontweight='bold')

    colors = plt.cm.Blues_r(np.linspace(0.2, 0.75, len(brand_counts)))


    ax1 = axs[0, 0]
    ax1.barh(brand_counts.index[::-1], brand_counts.values[::-1], color=colors[::-1])
    ax1.set_title('All Brands by Count', fontweight='bold')
    ax1.set_xlabel('Number of Listings')
    ax1.spines[['top','right']].set_visible(False)

    body_type_counts = df['body_type'].value_counts()
    ax2 = axs[0, 1]
    top5 = body_type_counts.head(5)
    rest = body_type_counts.iloc[5:].sum()
    pie_data = list(top5.values) + [rest]
    pie_labels = list(top5.index) + ['Others']
    ax2.pie(pie_data, labels=pie_labels, autopct='%1.1f%%', startangle=140,
            wedgeprops=dict(edgecolor='white', linewidth=1.5))
    ax2.set_title('Most Common Body Types', fontweight='bold')

    transmission_counts = df['transmission'].value_counts()
    top = transmission_counts
    ax3 = axs[1, 0]
    pcts = top / transmission_counts.sum() * 100
    bars = ax3.bar(top.index, top.values, color=colors[:5])
    for bar, pct in zip(bars, pcts.values):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100,
                f'{pct:.1f}%', ha='center', fontweight='bold', color='#1a6faf')
    ax3.set_title('Transmission Types', fontweight='bold')
    ax3.spines[['top','right']].set_visible(False)

    ax4 = axs[1, 1]
    fuel_type_counts = df['fuel_type'].value_counts()
    ax4.bar(fuel_type_counts.index, fuel_type_counts.values, color=colors)
    ax4.tick_params(axis='x', labelrotation=45)
    for label in ax4.get_xticklabels():
        label.set_ha('right')
    ax4.set_title('Most Common Fuel Types', fontweight='bold')
    ax4.spines[['top','right']].set_visible(False)
    st.pyplot(fig)



