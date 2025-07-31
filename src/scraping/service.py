"""
Scraping service with improved architecture and error handling.

This module provides a clean, maintainable service for scraping
thesis data from the UNHAS repository.
"""

import json
import time
from typing import Dict, Any, Optional

from selenium.webdriver.common.by import By

from ..core.abstractions import IScrapingService, ScrapingTarget, ProcessingResult, ProcessingStatus, ScrapingError
from ..core.webdriver import WebDriverService, get_element_text_or_none, get_table_value_by_header
from ..core.utils import FileNameGenerator, PathManager, PerformanceTimer
from ..config.service import ApplicationConfig


class ThesisData:
    """Data container for thesis information."""
    
    def __init__(self, title: str, url: str, faculty: str, major: str):
        self.title = title
        self.url = url
        self.faculty = faculty
        self.major = major
        self.author: Optional[str] = None
        self.abstract: Optional[str] = None
        self.item_type: Optional[str] = None
        self.date_deposited: Optional[str] = None
        self.last_modified: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert thesis data to dictionary."""
        return {
            "author": self.author,
            "abstract": self.abstract,
            "item_type": self.item_type,
            "date_deposited": self.date_deposited,
            "last_modified": self.last_modified,
            "url": self.url,
            "faculty": self.faculty,
            "major": self.major
        }


class UNHASScrapingService(IScrapingService):
    """Service for scraping thesis data from UNHAS repository."""
    
    def __init__(self, config: ApplicationConfig):
        """
        Initialize scraping service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.webdriver_service = WebDriverService(
            headless=config.scraping.headless_browser,
            verbose=config.verbose_logging
        )
    
    def scrape_repository(self, target: ScrapingTarget) -> ProcessingResult:
        """
        Scrape thesis data from repository.
        
        Args:
            target: Scraping target with faculty/major information
            
        Returns:
            Processing result with output file path
        """
        with PerformanceTimer(f"Repository scraping: {target.faculty_display} - {target.major_display}"):
            try:
                if self.config.verbose_logging:
                    print(f"🎓 Scraping {target.faculty_display} - {target.major_display}")
                    print(f"🔗 Target URL: {target.url}")
                
                with self.webdriver_service.get_driver() as driver:
                    # Navigate to target URL
                    driver.get(target.url)
                    time.sleep(3)
                    
                    # Extract all thesis data
                    repository_data = self._extract_repository_data(driver, target)
                    
                    # Save to file
                    output_file = self._save_repository_data(repository_data, target)
                    
                    return ProcessingResult(
                        status=ProcessingStatus.COMPLETED,
                        output_file=output_file,
                        metadata={
                            "faculty": target.faculty_display,
                            "major": target.major_display,
                            "total_theses": sum(len(year_data) for year_data in repository_data.values())
                        }
                    )
                    
            except Exception as e:
                error_msg = f"Failed to scrape repository: {e}"
                if self.config.verbose_logging:
                    print(f"❌ {error_msg}")
                
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error_message=error_msg
                )
    
    def scrape_faculty_major(self, faculty_key: str, major_key: str) -> ProcessingResult:
        """
        Scrape thesis data for a specific faculty and major.
        
        Args:
            faculty_key: Faculty key from configuration
            major_key: Major key from configuration
            
        Returns:
            ProcessingResult with output file path
        """
        try:
            # Create scraping target from faculty/major keys
            target = self._create_scraping_target(faculty_key, major_key)
            
            # Use the existing scrape_repository method
            return self.scrape_repository(target)
            
        except Exception as e:
            error_msg = f"Failed to scrape faculty/major {faculty_key}/{major_key}: {e}"
            if self.config.verbose_logging:
                print(f"❌ {error_msg}")
            
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=error_msg
            )
    
    def _create_scraping_target(self, faculty_key: str, major_key: str) -> ScrapingTarget:
        """Create a ScrapingTarget from faculty/major keys."""
        from ..discovery.service import get_faculty_display_name, get_major_display_name
        
        # Get faculty data
        if faculty_key not in self.config.faculties:
            raise ValueError(f"Faculty key '{faculty_key}' not found in configuration")
        
        faculty_data = self.config.faculties[faculty_key]
        faculty_display = get_faculty_display_name(self.config.faculties, faculty_key)
        
        # Get major data
        if isinstance(faculty_data, dict) and 'majors' in faculty_data:
            majors = faculty_data['majors']
        else:
            majors = faculty_data
        
        if major_key not in majors:
            raise ValueError(f"Major key '{major_key}' not found in faculty '{faculty_key}'")
        
        major_data = majors[major_key]
        major_display = get_major_display_name(major_key, major_data)
        
        # Get URL
        if isinstance(major_data, dict) and 'url' in major_data:
            url = major_data['url']
        elif isinstance(major_data, str):
            url = major_data
        else:
            raise ValueError(f"Cannot determine URL for major '{major_key}'")
        
        return ScrapingTarget(
            faculty_key=faculty_key,
            major_key=major_key,
            faculty_display=faculty_display,
            major_display=major_display,
            url=url
        )
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if hasattr(self, 'webdriver_service') and self.webdriver_service:
                self.webdriver_service.cleanup()
        except Exception as e:
            if self.config.verbose_logging:
                print(f"⚠️  Cleanup warning: {e}")
    
    def extract_thesis_data(self, url: str) -> Dict[str, Any]:
        """
        Extract data from a single thesis page.
        
        Args:
            url: URL of thesis page
            
        Returns:
            Thesis data dictionary
        """
        with self.webdriver_service.get_driver() as driver:
            driver.get(url)
            time.sleep(self.config.scraping.delay)
            
            return self._extract_single_thesis_data(driver, url)
    
    def _extract_repository_data(self, driver, target: ScrapingTarget) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Extract all thesis data from repository."""
        repository_data = {}
        
        # Find all year links on the main page
        year_elements = self.webdriver_service.safe_find_elements(
            driver, By.XPATH, "/html/body/div[1]/div/div[2]/div/ul/li/a"
        )
        
        year_links = []
        for elem in year_elements:
            year_text = self.webdriver_service.safe_get_text(elem)
            year_url = self.webdriver_service.safe_get_attribute(elem, 'href')
            if year_text and year_url:
                year_links.append((year_text, year_url))
        
        if self.config.verbose_logging:
            print(f"📅 Found {len(year_links)} years to process")
        
        # Process each year
        for year_text, year_url in year_links:
            # Always show year processing to user
            print(f"\n📋 Processing Year: {year_text}")
            
            repository_data[year_text] = {}
            driver.get(year_url)
            time.sleep(2)
            
            # Extract thesis URLs for this year
            thesis_urls = self._extract_thesis_urls_for_year(driver)
            
            # Always show thesis count to user
            print(f"   Found {len(thesis_urls)} theses")
            
            # Process each thesis
            for i, thesis_url in enumerate(thesis_urls, 1):
                thesis_data = self._process_single_thesis(driver, thesis_url, target, i, len(thesis_urls))
                if thesis_data:
                    repository_data[year_text][thesis_data.title] = thesis_data.to_dict()
        
        return repository_data
    
    def _extract_thesis_urls_for_year(self, driver) -> list:
        """Extract all thesis URLs for a given year."""
        thesis_urls = []
        thesis_index = 1
        
        while True:
            try:
                xpath = f"/html/body/div[1]/div/div[2]/div[2]/p[{thesis_index}]/a"
                thesis_link_element = self.webdriver_service.safe_find_element(driver, By.XPATH, xpath)
                
                if thesis_link_element:
                    url = self.webdriver_service.safe_get_attribute(thesis_link_element, 'href')
                    if url:
                        thesis_urls.append(url)
                    thesis_index += 1
                else:
                    break  # No more thesis links found
                    
            except Exception:
                break  # Exit loop on any error
        
        return thesis_urls
    
    def _process_single_thesis(self, driver, thesis_url: str, target: ScrapingTarget, 
                             index: int, total: int) -> Optional[ThesisData]:
        """Process a single thesis page."""
        try:
            driver.get(thesis_url)
            time.sleep(self.config.scraping.delay)
            
            # Extract title
            title = get_element_text_or_none(driver, '//*[@id="page-title"]')
            if not title:
                # Always show skipped entries
                print(f"  - Skipping entry {index}/{total} (Title not found)")
                return None
            
            # Always show scraping progress to user
            print(f"  - Scraping [{index}/{total}]: {title[:60]}...")
            
            # Create thesis data object
            thesis_data = ThesisData(title, thesis_url, target.faculty_key, target.major_key)
            
            # Extract detailed information
            thesis_data.author = get_element_text_or_none(
                driver, "/html/body/div[1]/div/div[2]/div/div[4]/p/span"
            )
            thesis_data.abstract = get_element_text_or_none(
                driver, "/html/body/div[1]/div/div[2]/div/div[4]/div[3]/p"
            )
            thesis_data.item_type = get_table_value_by_header(driver, "Item Type:")
            thesis_data.date_deposited = get_table_value_by_header(driver, "Date Deposited:")
            thesis_data.last_modified = get_table_value_by_header(driver, "Last Modified:")
            
            return thesis_data
            
        except Exception as e:
            if self.config.verbose_logging:
                print(f"  - Error processing thesis {index}/{total}: {e}")
            return None
    
    def _extract_single_thesis_data(self, driver, url: str) -> Dict[str, Any]:
        """Extract data from a single thesis page (for external use)."""
        thesis_data = ThesisData("", url, "", "")
        
        thesis_data.title = get_element_text_or_none(driver, '//*[@id="page-title"]') or ""
        thesis_data.author = get_element_text_or_none(
            driver, "/html/body/div[1]/div/div[2]/div/div[4]/p/span"
        )
        thesis_data.abstract = get_element_text_or_none(
            driver, "/html/body/div[1]/div/div[2]/div/div[4]/div[3]/p"
        )
        thesis_data.item_type = get_table_value_by_header(driver, "Item Type:")
        thesis_data.date_deposited = get_table_value_by_header(driver, "Date Deposited:")
        thesis_data.last_modified = get_table_value_by_header(driver, "Last Modified:")
        
        return thesis_data.to_dict()
    
    def _save_repository_data(self, repository_data: Dict[str, Any], target: ScrapingTarget) -> str:
        """Save repository data to JSON file."""
        from ..core.abstractions import OperationType
        
        # Generate filename
        filename = FileNameGenerator.generate_filename(
            OperationType.SCRAPE,
            target.faculty_key,
            target.major_key,
            extension="json"
        )
        
        # Resolve output path
        output_file = PathManager.resolve_output_path(self.config.processing.output_dir, filename)
        
        # Save data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(repository_data, f, ensure_ascii=False, indent=4)
        
        if self.config.verbose_logging:
            total_theses = sum(len(year_data) for year_data in repository_data.values())
            print(f"\n✅ Scraping complete: {total_theses} theses saved to '{output_file}'")
        
        return output_file
