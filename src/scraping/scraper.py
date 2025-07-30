

import json
import time
import os
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def get_element_text_or_none(driver, xpath):
    """Safely gets text from an element by its full XPath."""
    try:
        return driver.find_element(By.XPATH, xpath).text.strip()
    except NoSuchElementException:
        return None


def get_table_value_by_header(driver, header_text):
    """
    Finds a table row by its header text and returns the value from the next cell.
    This is more reliable than using a fixed row index.
    """
    try:
        # This XPath finds a <th> containing the header_text, then gets the text of the <td> next to it.
        xpath = f"//th[contains(text(), '{header_text}')]/following-sibling::td"
        return driver.find_element(By.XPATH, xpath).text.strip()
    except NoSuchElementException:
        return None


def scrape_repository(output_dir="output"):
    """
    Scrapes thesis data from the UNHAS Statistics repository.
    """
    # Automatically install and set up the ChromeDriver
    service = ChromeService(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Optional: run in background
    options.add_argument("--log-level=3")  # Suppress console logs
    driver = webdriver.Chrome(service=service, options=options)

    base_url = "https://repository.unhas.ac.id/view/divisions/statistika/"
    print(f"Navigating to {base_url}...")
    driver.get(base_url)
    time.sleep(3)

    repository_data = {}

    # Find all year links on the main page to avoid stale elements
    year_elements = driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div/ul/li/a")
    year_links = [(elem.text, elem.get_attribute('href')) for elem in year_elements]

    # Loop 1: Iterate through each year
    for year_text, year_url in year_links:
        print(f"\nProcessing Year: {year_text}")
        repository_data[year_text] = {}
        driver.get(year_url)
        time.sleep(2)

        thesis_urls = []
        thesis_index = 1
        # Loop 2: Find all thesis links for the current year
        while True:
            try:
                xpath = f"/html/body/div[1]/div/div[2]/div[2]/p[{thesis_index}]/a"
                thesis_link_element = driver.find_element(By.XPATH, xpath)
                thesis_urls.append(thesis_link_element.get_attribute('href'))
                thesis_index += 1
            except NoSuchElementException:
                break  # Exit loop when no more thesis links are found

        # Loop 3: Visit each thesis page and scrape data
        for i, thesis_url in enumerate(thesis_urls):
            driver.get(thesis_url)
            time.sleep(1)

            title = get_element_text_or_none(driver, '//*[@id="page-title"]')
            if not title:
                print(f"  - Skipping entry {i+1}/{len(thesis_urls)} (Title not found)")
                continue

            print(f"  - Scraping [{i+1}/{len(thesis_urls)}]: {title[:60]}...")

            # Scrape all required details using the new robust method for table data
            thesis_details = {
                "author": get_element_text_or_none(driver, "/html/body/div[1]/div/div[2]/div/div[4]/p/span"),
                "abstract": get_element_text_or_none(driver, "/html/body/div[1]/div/div[2]/div/div[4]/div[3]/p"),
                "item_type": get_table_value_by_header(driver, "Item Type:"),
                "date_deposited": get_table_value_by_header(driver, "Date Deposited:"),
                "last_modified": get_table_value_by_header(driver, "Last Modified:"),
                "url": thesis_url
            }

            repository_data[year_text][title] = thesis_details

    # Save the final data structure to a JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(output_dir, f'unhas_repository_{timestamp}.json')
    os.makedirs(output_dir, exist_ok=True)
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(repository_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Scraping complete. Data has been saved to '{output_filename}'.")
    driver.quit()
    return output_filename

