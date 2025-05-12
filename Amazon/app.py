import streamlit as st
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from amazon_scraper import scrape_amazon_products  # we’ll create this in a separate file

st.set_page_config(page_title="Amazon Product Scraper", layout="wide")

st.title("🛒 Amazon Sponsored Product Scraper & Analyzer")
product_name = st.text_input("Enter Product Keyword (e.g., soft toys)", "")

if st.button("Scrape & Analyze") and product_name:
    with st.spinner("Scraping data... please wait."):
        df = scrape_amazon_products(product_name)
        if df.empty:
            st.error("No sponsored products found.")
        else:
            st.success(f"{len(df)} products scraped!")

            # Show Data Table
            st.subheader("📊 Scraped Data Preview")
            st.dataframe(df)

            # Download Button
            csv = df.to_csv(index=False).encode()
            st.download_button("📥 Download CSV", csv, f"{product_name}_sponsored_products.csv", "text/csv")

            # --- Brand Analysis ---
            st.subheader("🏷️ Brand Performance")
            top_brands = df['Brand'].value_counts().nlargest(5)
            avg_rating_by_brand = df.groupby('Brand')['Rating'].mean().dropna().sort_values(ascending=False).head(5)

            col1, col2 = st.columns(2)
            with col1:
                st.bar_chart(top_brands)
            with col2:
                fig, ax = plt.subplots()
                ax.pie(top_brands, labels=top_brands.index, autopct='%1.1f%%', startangle=140)
                ax.axis('equal')  # Equal aspect ratio for a perfect circle
                st.pyplot(fig)

            # --- Price vs Rating ---
            st.subheader("💸 Price vs. Rating")
            fig, ax = plt.subplots()
            sns.scatterplot(data=df, x="Rating", y="Selling Price", hue="Brand", ax=ax)
            st.pyplot(fig)

            price_bins = pd.cut(df['Rating'], bins=[0, 2, 3, 4, 5], labels=["0-2", "2-3", "3-4", "4-5"])
            avg_price = df.groupby(price_bins)['Selling Price'].mean()

            st.bar_chart(avg_price)

            # --- Top Products ---
            st.subheader("🌟 Top Products")
            top_rated = df.sort_values(by="Rating", ascending=False).head(5)[['Title', 'Rating']]
            top_reviewed = df.sort_values(by="Reviews", ascending=False).head(5)[['Title', 'Reviews']]

            col1, col2 = st.columns(2)
            with col1:
                st.write("Top Rated Products")
                st.dataframe(top_rated)
            with col2:
                st.write("Most Reviewed Products")
                st.dataframe(top_reviewed)
