# amazon_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_amazon_products(search_term):
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    url = f"https://www.amazon.in/s?k={search_term.replace(' ', '+')}"
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-main-slot")))
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    products = soup.find_all('div', {'data-component-type': 's-search-result'})

    data = []
    for product in products:
        try:
            if product.find('span', string="Sponsored"):
                continue

            asin = product.get('data-asin')
            product_url = f"https://www.amazon.in/dp/{asin}" if asin else None

            h2_tag = product.find('h2')
            title_tag = h2_tag.find('span') if h2_tag else None
            title = title_tag.text.strip() if title_tag else "No Title"

            brand = product.get('data-brand')
            if not brand:
                brand_span = product.select_one("div.a-row.a-size-base.a-color-secondary span")
                if brand_span and not any(char.isdigit() for char in brand_span.text.strip()):
                    brand = brand_span.text.strip()
            if not brand and title:
                brand = title.split()[0]
            if not brand:
                brand = "Unknown"

            rating_tag = product.find('span', class_='a-icon-alt')
            rating = float(rating_tag.text.split()[0]) if rating_tag else None

            review_tag = product.find('span', {'class': 'a-size-base'})
            reviews = int(review_tag.text.replace(",", "")) if review_tag and review_tag.text.replace(",", "").isdigit() else 0

            price_tag = product.find('span', class_='a-price-whole')
            price = int(price_tag.text.replace(",", "").replace("₹", "")) if price_tag else None

            image_tag = product.find('img')
            image_url = image_tag['src'] if image_tag else None

            data.append({
                'Title': title,
                'Brand': brand,
                'Rating': rating,
                'Reviews': reviews,
                'Selling Price': price,
                'Image URL': image_url,
                'Product URL': product_url
            })

        except Exception:
            continue

    driver.quit()
    return pd.DataFrame(data)
