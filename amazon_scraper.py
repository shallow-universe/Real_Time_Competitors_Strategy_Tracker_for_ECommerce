"""
Production-ready Amazon mobile data + review scraper.
Saves to My_docs/ folder, with error handling and deduplication.
"""

import os, re, time
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ------------------------------
# CONFIG
# ------------------------------
SEARCH_URL = "https://www.amazon.in/s?k=mobiles&page={}"
LISTING_PAGES = 5        # number of search pages
REVIEW_PAGES = 3         # reviews per product
WAIT = 3                 # wait after page load
OUTPUT_DIR = "My_docs"   # save folder

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------
# Selenium setup
# ------------------------------
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(options=options)

# ------------------------------
# Helpers
# ------------------------------
def clean_price(txt):
    """Extract digits from price string."""
    return re.sub(r"[^\d]", "", txt) if txt else None

def save_csv(df_new, path, subset_cols):
    """Append to CSV if exists, drop duplicates by subset_cols."""
    if os.path.exists(path):
        df_old = pd.read_csv(path)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    if subset_cols:
        df = df.drop_duplicates(subset=subset_cols, keep="last")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"✅ Saved {len(df_new)} new rows (total {len(df)}) → {path}")

# ------------------------------
# Step 1: Collect product listings
# ------------------------------
mobile_rows, product_links = [], set()
scraped_at = datetime.utcnow().isoformat()

for page in range(1, LISTING_PAGES + 1):
    print(f"📄 Scraping listing page {page}")
    driver.get(SEARCH_URL.format(page))
    time.sleep(WAIT)
    soup = BeautifulSoup(driver.page_source, "lxml")

    products = soup.find_all("div", {"data-component-type": "s-search-result"})
    for p in products:
        asin = p.get("data-asin")
        title = p.find("span", {"class": "a-size-medium"})
        if not title:
            title = p.find("span", {"class": "a-size-base-plus a-color-base a-text-normal"})
        if not title and p.find("h2"):
        # Sometimes the title is inside <h2>
            title = p.find("h2").find("span")
        price = p.find("span", {"class": "a-price-whole"})
        mrp = p.find("span", {"class": "a-text-price"})
        rating = p.find("span", {"class": "a-icon-alt"})
        link = p.find("a", {"class": "a-link-normal"}, href=True)

        mobilename = title.get_text(strip=True) if title else "Unknown"
        sellingprice = clean_price(price.get_text()) if price else None
        mrp_val = mrp.get_text(strip=True).replace("₹", "").replace(",", "") if mrp else None
        rating_val = rating.get_text(strip=True) if rating else None
        url = "https://www.amazon.in" + link["href"] if link else None

    '''for p in products:
       asin = p.get("data-asin")
    
    # Try multiple ways to get the title
    title = p.find("span", {"class": "a-size-medium"})
    if not title:
        title = p.find("span", {"class": "a-size-base-plus a-color-base a-text-normal"})
    if not title and p.find("h2"):
        # Sometimes the title is inside <h2>
        title = p.find("h2").find("span")
        
    mobilename = title.get_text(strip=True) if title else "Unknown"
    
    # Price
    price = p.find("span", {"class": "a-price-whole"})
    sellingprice = clean_price(price.get_text()) if price else None

    # MRP / list price
    mrp = p.find("span", {"class": "a-text-price"})
    mrp_val = mrp.get_text(strip=True).replace("₹", "").replace(",", "") if mrp else None

    # Rating
    rating = p.find("span", {"class": "a-icon-alt"})
    rating_val = rating.get_text(strip=True) if rating else None

    # Link
    link = p.find("a", {"class": "a-link-normal"}, href=True)
    url = "https://www.amazon.in" + link["href"] if link else None'''


    if asin and url:
        product_links.add((asin, mobilename, url))

        mobile_rows.append({
            "source": "amazon",
            "productid": asin,
            "mobilename": mobilename,
            "sellingprice": sellingprice,
            "mrp": mrp_val,
            "discountoffering": None,  # Amazon doesn’t show % off directly
            "rating": rating_val,
            "url": url,
            "scraped_at": scraped_at
        })

# save product listings
mobile_df = pd.DataFrame(mobile_rows)
save_csv(mobile_df, os.path.join(OUTPUT_DIR, "mobile.csv"), ["productid", "scraped_at"])

# ------------------------------
# Step 2: Collect product reviews
# ------------------------------
review_rows = []

for pid, name, url in product_links:
    if not url:
        continue
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "reviews-medley-footer")))
        soup = BeautifulSoup(driver.page_source, "lxml")

        # Extract "See all reviews" link
        all_reviews = soup.find("a", href=re.compile("/product-reviews/"))
        if not all_reviews:
            continue

        reviews_base = "https://www.amazon.in" + all_reviews["href"]
        print(f"💬 Scraping reviews for {name}")

        for rpage in range(1, REVIEW_PAGES + 1):
            driver.get(f"{reviews_base}&pageNumber={rpage}")
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "review")))
            except TimeoutException:
                break

            rsoup = BeautifulSoup(driver.page_source, "lxml")
            containers = rsoup.find_all("div", {"data-hook": "review"})

            for c in containers:
                user = c.find("span", {"class": "a-profile-name"})
                rating = c.find("i", {"data-hook": "review-star-rating"})
                text = c.find("span", {"data-hook": "review-body"})
                date = c.find("span", {"data-hook": "review-date"})

                review_rows.append({
                    "source": "amazon",
                    "productid": pid,
                    "mobilename": name,
                    "userid": user.get_text(strip=True) if user else "Anonymous",
                    "review": text.get_text(strip=True) if text else "",
                    "rating": rating.get_text(strip=True) if rating else None,
                    "reviewdate": date.get_text(strip=True) if date else ""
                })
            time.sleep(1)
    except Exception as e:
        print(f"⚠ Error scraping {name}: {e}")

driver.quit()

# save reviews
review_df = pd.DataFrame(review_rows)
save_csv(review_df, os.path.join(OUTPUT_DIR, "review.csv"), ["productid", "userid", "review"])

# ------------------------------
# Optional ingestion call
# ------------------------------
try:
    import ingestion
    ingestion.main()
except ImportError:
    print("ℹ ingestion.py not found, skipping ingestion step.")
