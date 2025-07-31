"""
Web driver service with improved resource management and configuration.

This module provides a clean abstraction for web driver operations with
proper resource management, error handling, and performance optimization.
"""

import os
import logging
import tempfile
import uuid
from typing import Optional, List, Any
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from ..core.utils import suppress_output


class WebDriverService:
    """Enhanced web driver service with better resource management."""
    
    def __init__(self, headless: bool = True, verbose: bool = False):
        """
        Initialize web driver service.
        
        Args:
            headless: Whether to run browser in headless mode
            verbose: Whether to enable verbose logging
        """
        self.headless = headless
        self.verbose = verbose
        self.driver: Optional[webdriver.Chrome] = None
        self._temp_dir: Optional[str] = None
        
        # Suppress logging for cleaner output
        self._configure_logging()
    
    def _configure_logging(self) -> None:
        """Configure logging to reduce noise."""
        loggers = ['selenium', 'urllib3', 'webdriver_manager']
        for logger_name in loggers:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        
        # Suppress Chrome DevTools messages
        os.environ['WDM_LOG'] = '0'
        os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
    
    def _create_chrome_options(self) -> ChromeOptions:
        """Create optimized Chrome options."""
        options = ChromeOptions()
        
        # Basic options
        if self.headless:
            options.add_argument("--headless")
        
        # Performance and stability options
        performance_options = [
            "--log-level=3",
            "--silent", 
            "--disable-logging",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-web-security", 
            "--disable-features=VizDisplayCompositor"
        ]
        
        for option in performance_options:
            options.add_argument(option)
        
        # Disable various features for better performance
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Notification preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        # Create unique user data directory to prevent conflicts
        self._temp_dir = self._create_temp_directory()
        options.add_argument(f"--user-data-dir={self._temp_dir}")
        
        return options
    
    def _create_temp_directory(self) -> str:
        """Create unique temporary directory for browser data."""
        temp_base = tempfile.gettempdir()
        unique_id = uuid.uuid4().hex[:8]
        return os.path.join(temp_base, f"chrome_unhas_scraper_{unique_id}")
    
    def _create_chrome_service(self) -> ChromeService:
        """Create Chrome service with optimized settings."""
        service = ChromeService(ChromeDriverManager().install())
        
        # Windows-specific optimization
        if os.name == 'nt':
            service.creation_flags = 0x08000000  # CREATE_NO_WINDOW flag
        
        return service
    
    @contextmanager
    def get_driver(self):
        """
        Context manager for web driver with automatic cleanup.
        
        Yields:
            WebDriver instance
        """
        try:
            if self.verbose:
                print("🌐 Initializing web driver...")
            
            service = self._create_chrome_service()
            options = self._create_chrome_options()
            
            # Create driver with suppressed output
            with suppress_output():
                self.driver = webdriver.Chrome(service=service, options=options)
            
            if self.verbose:
                print("✅ Web driver initialized successfully")
            
            yield self.driver
            
        finally:
            self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                if self.verbose:
                    print("🧹 Web driver closed successfully")
            except Exception as e:
                if self.verbose:
                    print(f"⚠️  Warning during driver cleanup: {e}")
            finally:
                self.driver = None
        
        # Clean up temporary directory
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass  # Ignore cleanup errors
    
    def safe_find_element(self, driver: webdriver.Chrome, by: str, value: str) -> Optional[Any]:
        """
        Safely find element without raising exceptions.
        
        Args:
            driver: WebDriver instance
            by: Locator strategy
            value: Locator value
            
        Returns:
            Element if found, None otherwise
        """
        try:
            return driver.find_element(by, value)
        except NoSuchElementException:
            return None
    
    def safe_find_elements(self, driver: webdriver.Chrome, by: str, value: str) -> List[Any]:
        """
        Safely find elements without raising exceptions.
        
        Args:
            driver: WebDriver instance
            by: Locator strategy
            value: Locator value
            
        Returns:
            List of elements (empty list if none found)
        """
        try:
            return driver.find_elements(by, value)
        except NoSuchElementException:
            return []
    
    def safe_get_text(self, element: Any) -> str:
        """
        Safely get text from element.
        
        Args:
            element: Web element
            
        Returns:
            Element text or empty string if error
        """
        try:
            return element.text.strip() if element else ""
        except Exception:
            return ""
    
    def safe_get_attribute(self, element: Any, attribute: str) -> str:
        """
        Safely get attribute from element.
        
        Args:
            element: Web element
            attribute: Attribute name
            
        Returns:
            Attribute value or empty string if error
        """
        try:
            return element.get_attribute(attribute) if element else ""
        except Exception:
            return ""


class ElementLocator:
    """Utility class for managing element locators."""
    
    # Common XPaths used in scraping
    THESIS_TITLE = '//*[@id="page-title"]'
    THESIS_AUTHOR = "/html/body/div[1]/div/div[2]/div/div[4]/p/span"
    THESIS_ABSTRACT = "/html/body/div[1]/div/div[2]/div/div[4]/div[3]/p"
    
    @staticmethod
    def get_thesis_link_xpath(index: int) -> str:
        """Get XPath for thesis link by index."""
        return f"/html/body/div[1]/div/div[2]/div[2]/p[{index}]/a"
    
    @staticmethod
    def get_year_links_xpath() -> str:
        """Get XPath for year links."""
        return "/html/body/div[1]/div/div[2]/div/ul/li/a"
    
    @staticmethod
    def get_faculty_links_xpath() -> str:
        """Get XPath for faculty links in discovery."""
        return "./li/a"
    
    @staticmethod
    def get_major_links_xpath() -> str:
        """Get XPath for major links in discovery."""
        return "./ul/li/a"


def get_element_text_or_none(driver: webdriver.Chrome, xpath: str) -> Optional[str]:
    """
    Safely get text from element by XPath.
    
    Args:
        driver: WebDriver instance
        xpath: XPath expression
        
    Returns:
        Element text or None if not found
    """
    web_service = WebDriverService()
    element = web_service.safe_find_element(driver, By.XPATH, xpath)
    return web_service.safe_get_text(element) if element else None


def get_table_value_by_header(driver: webdriver.Chrome, header_text: str) -> Optional[str]:
    """
    Get table value by header text using robust method.
    
    Args:
        driver: WebDriver instance
        header_text: Header text to search for
        
    Returns:
        Value from table or None if not found
    """
    try:
        # Find all table rows
        rows = driver.find_elements(By.XPATH, "//tr")
        
        for row in rows:
            # Check if this row contains our header
            header_cells = row.find_elements(By.XPATH, ".//th | .//td")
            
            for i, cell in enumerate(header_cells):
                if header_text.lower() in cell.text.lower():
                    # Found header, try to get value from next cell
                    if i + 1 < len(header_cells):
                        return header_cells[i + 1].text.strip()
                    
                    # If no next cell in same row, check next row
                    try:
                        next_row = row.find_element(By.XPATH, "./following-sibling::tr[1]")
                        value_cells = next_row.find_elements(By.XPATH, ".//th | .//td")
                        if value_cells:
                            return value_cells[0].text.strip()
                    except NoSuchElementException:
                        pass
        
        return None
        
    except Exception:
        return None
    
    def cleanup(self) -> None:
        """Clean up webdriver resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
