

import json
import time
import os
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import Config


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


def scrape_repository(output_dir: str = "output", config: Config = None, 
                     faculty: str = None, major: str = None) -> str:
    """
    Scrapes thesis data from the UNHAS repository.
    
    Args:
        output_dir: Directory to save output files
        config: Configuration object (optional, will use defaults if not provided)
        faculty: Faculty name (overrides config if provided)
        major: Major name (overrides config if provided)
        
    Returns:
        Path to the created JSON file
    """
    # Determine target URL
    if config is not None:
        from .discovery import resolve_faculty_name_to_key, resolve_major_name_to_key
        
        target_faculty_input = faculty or config.target_faculty
        target_major_input = major or config.target_major
        headless = config.headless_browser
        delay = config.scraping_delay
        
        # Resolve faculty name to configuration key
        try:
            target_faculty = resolve_faculty_name_to_key(config.faculties, target_faculty_input)
        except ValueError as e:
            raise ValueError(str(e))
        
        faculty_data = config.faculties[target_faculty]
        
        # Handle new nested structure vs old flat structure
        if isinstance(faculty_data, dict) and 'majors' in faculty_data:
            # New nested structure
            majors = faculty_data['majors']
            
            # Resolve major name to configuration key
            try:
                target_major = resolve_major_name_to_key(majors, target_major_input)
            except ValueError as e:
                raise ValueError(str(e))
            
            major_info = majors[target_major]
            if isinstance(major_info, dict) and 'url' in major_info:
                base_url = major_info['url']
            else:
                base_url = major_info
        else:
            # Old flat structure
            try:
                target_major = resolve_major_name_to_key(faculty_data, target_major_input)
            except ValueError as e:
                raise ValueError(str(e))
            
            major_info = faculty_data[target_major]
            if isinstance(major_info, dict) and 'url' in major_info:
                base_url = major_info['url']
            else:
                base_url = major_info
                
    else:
        # Legacy behavior - default to Statistics
        target_faculty = faculty or "mipa"
        target_major = major or "statistika"
        headless = True
        delay = 1.0
        base_url = "https://repository.unhas.ac.id/view/divisions/statistika/"
        print("Warning: Using legacy mode. Consider providing a Config object for better flexibility.")

    # Automatically install and set up the ChromeDriver with logging suppression
    import logging
    import tempfile
    import uuid
    from contextlib import contextmanager
    
    @contextmanager
    def suppress_output():
        """Context manager to suppress stdout and stderr."""
        import sys
        if os.name == 'nt':  # Windows
            try:
                # Temporarily redirect stderr to devnull
                old_stderr = sys.stderr
                sys.stderr = open('NUL', 'w')
                yield
            finally:
                if sys.stderr != old_stderr:
                    sys.stderr.close()
                sys.stderr = old_stderr
        else:
            # Unix/Linux
            try:
                old_stderr = sys.stderr
                sys.stderr = open('/dev/null', 'w')
                yield
            finally:
                if sys.stderr != old_stderr:
                    sys.stderr.close()
                sys.stderr = old_stderr
    
    # Suppress Selenium and WebDriver logging
    logging.getLogger('selenium').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('webdriver_manager').setLevel(logging.CRITICAL)
    
    # Suppress Chrome DevTools messages
    os.environ['WDM_LOG'] = '0'
    os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
    
    service = ChromeService(ChromeDriverManager().install())
    service.creation_flags = 0x08000000  # CREATE_NO_WINDOW flag for Windows
    
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2
        }
    }
    options.add_experimental_option("prefs", prefs)
    
    # Add unique user data directory to prevent session conflicts
    temp_dir = tempfile.gettempdir()
    user_data_dir = os.path.join(temp_dir, f"chrome_unhas_scraper_{uuid.uuid4().hex[:8]}")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Create driver with suppressed output
    with suppress_output():
        driver = webdriver.Chrome(service=service, options=options)

    print(f"Scraping {target_faculty} - {target_major}")
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
            time.sleep(delay)

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
                "url": thesis_url,
                "faculty": target_faculty,
                "major": target_major
            }

            repository_data[year_text][title] = thesis_details

    # Save the final data structure to a JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_suffix = f"{target_faculty}_{target_major}_{timestamp}" if config else f"unhas_repository_{timestamp}"
    output_filename = os.path.join(output_dir, f'{filename_suffix}.json')
    os.makedirs(output_dir, exist_ok=True)
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(repository_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Scraping complete. Data has been saved to '{output_filename}'.")
    driver.quit()
    return output_filename

