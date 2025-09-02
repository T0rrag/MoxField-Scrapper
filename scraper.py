# LIBRARY DIVISION
import csv
import time
import random
import re
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchWindowException, WebDriverException, ElementClickInterceptedException

# DATA DIVISION
URL = "https://moxfield.com/decks/public?q=eyJmb3JtYXQiOiJjb21tYW5kZXJQcmVjb25zIn0%3D"
OUTPUT_CSV = "EDH_Precon_list.csv"
LOAD_MORE_PAUSE = 3  # Increased pause for stability
MAX_CLICKS = 3  # Limit to 3 clicks as specified
TIMEOUT = 20
SCROLL_PAUSE = 1

# START DIVISION
options = Options()
# Comment out headless for debugging
# options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

# PROCEDURE DIVISION
try:
    print("Loading page...")
    try:
        driver.get(URL)
        time.sleep(10)  # Initial delay for page load
    except NoSuchWindowException:
        print("Error: Browser window closed during page load. Retrying...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(URL)
        time.sleep(10)

    print("Waiting for deck elements to load...")
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/decks/']"))
        )
    except Exception as e:
        print(f"Error: Deck elements not found within {TIMEOUT} seconds. Possible issues:")
        print("- CSS selector 'a[href^='/decks/']' may be incorrect.")
        print("- Page may not have loaded fully or is blocked by anti-bot measures.")
        print(f"Exception: {e}")
        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            print(f"Found {len(all_links)} <a> elements. First 5 links:")
            for i, link in enumerate(all_links[:5]):
                href = link.get_attribute("href") or "No href"
                print(f"Link {i+1}: {href}")
        except NoSuchWindowException:
            print("Error: Browser window closed while logging links.")
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Saved page source to 'page_source.html' for debugging.")
        raise

    print("Clicking 'View More' to load all decks...")
    click_count = 0
    while click_count < MAX_CLICKS:
        try:
            # Incremental scrolling to ensure "View More" is visible
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(5):  # Increased scrolling attempts
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(SCROLL_PAUSE)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # Try to find the "View More" button
            load_more = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'View More')]]"))
            )
            # Log the button's details for debugging
            button_class = load_more.get_attribute('class')
            button_text = load_more.text
            is_displayed = load_more.is_displayed()
            is_enabled = load_more.is_enabled()
            print(f"Found 'View More' button with class: {button_class}, text: {button_text}, displayed: {is_displayed}, enabled: {is_enabled}")
            try:
                load_more.click()
            except ElementClickInterceptedException:
                print("Selenium click failed. Trying JavaScript click...")
                driver.execute_script("arguments[0].click();", load_more)
            click_count += 1
            print(f"Clicked 'View More' {click_count} time(s).")
            time.sleep(LOAD_MORE_PAUSE)
        except (NoSuchWindowException, WebDriverException):
            print("Error: Browser window closed during 'View More' click. Proceeding to scrape visible decks.")
            break
        except:
            print("No 'View More' button found or all content loaded. Trying fallback selector...")
            try:
                load_more = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-secondary"))
                )
                button_class = load_more.get_attribute('class')
                button_text = load_more.text
                is_displayed = load_more.is_displayed()
                is_enabled = load_more.is_enabled()
                print(f"Found fallback 'View More' button with class: {button_class}, text: {button_text}, displayed: {is_displayed}, enabled: {is_enabled}")
                try:
                    load_more.click()
                except ElementClickInterceptedException:
                    print("Selenium click failed. Trying JavaScript click...")
                    driver.execute_script("arguments[0].click();", load_more)
                click_count += 1
                print(f"Clicked 'View More' {click_count} time(s).")
                time.sleep(LOAD_MORE_PAUSE)
            except:
                print("No fallback 'View More' button found. Proceeding to scrape visible decks.")
                break

    print("Collecting deck links and names...")
    try:
        link_elems = driver.find_elements(By.CSS_SELECTOR, "a[href^='/decks/']")
        print(f"Found {len(link_elems)} potential deck links.")
    except NoSuchWindowException:
        print("Error: Browser window closed while collecting deck links.")
        raise

    deck_data = []
    for i, link in enumerate(link_elems):
        try:
            href = link.get_attribute("href")
            if not href:
                continue
            parsed = urlparse(href)
            parts = [p for p in parsed.path.split('/') if p]
            if len(parts) >= 2 and parts[0] == "decks" and parts[1] != "public":
                # Extract deck name from the span with class MKZh9kXyTHLRH7IyZaX8
                try:
                    name_elem = link.find_element(By.CSS_SELECTOR, "span.MKZh9kXyTHLRH7IyZaX8")
                    full_name = name_elem.get_attribute('title') or name_elem.text  # Prefer title for full name
                    # Clean the name: remove parenthetical text, trailing ellipsis, and extra spaces
                    deck_name = re.sub(r'\s*\([^)]*\)', '', full_name).replace('...', '').strip()
                    print(f"Raw deck name: {full_name}, Cleaned: {deck_name}")  # Debug log
                except:
                    deck_name = parts[1]  # Fallback to URL deck ID
                    print(f"Warning: Could not find deck name for {href}, using ID: {deck_name}")

                normalized_url = f"https://moxfield.com/decks/{parts[1]}"
                deck_data.append((deck_name, normalized_url))
                if i < 5:  # Log first 5 for debugging
                    print(f"Deck {i+1}: {deck_name} | {normalized_url}")
        except NoSuchWindowException:
            print("Error: Browser window closed while processing deck links.")
            raise

    print("Saving deck links to CSV...")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, delimiter=",")
        writer.writerow(["deck_id", "url"])  # Headers
        for deck_name, url in sorted(deck_data, key=lambda x: x[0]):
            writer.writerow([deck_name, url])

    print(f"✅ Saved {len(deck_data)} deck links to {OUTPUT_CSV}")

finally:
    print("Closing browser...")
    try:
        driver.quit()
    except:
        print("Browser already closed.")