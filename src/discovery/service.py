"""
Refactored discovery service with improved architecture and error handling.

This module provides a clean, maintainable service for discovering
faculties and majors from the UNHAS repository website.
"""

import time
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By

from ..core.abstractions import IDiscoveryService, ScrapingError
from ..core.webdriver import WebDriverService
from ..core.utils import TextSanitizer, PerformanceTimer
from ..config.service import ApplicationConfig


class UNHASDiscoveryService(IDiscoveryService):
    """Service for discovering faculties and majors from UNHAS repository."""
    
    BASE_URL = "https://repository.unhas.ac.id/view/divisions/"
    
    def __init__(self, headless: bool = True, verbose: bool = False):
        """
        Initialize discovery service.
        
        Args:
            headless: Whether to run browser in headless mode
            verbose: Whether to enable verbose logging
        """
        self.webdriver_service = WebDriverService(headless, verbose)
        self.verbose = verbose
    
    def discover_faculties(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover all available faculties.
        
        Returns:
            Dictionary mapping faculty keys to faculty information
            
        Raises:
            ScrapingError: If discovery fails
        """
        with PerformanceTimer("Faculty discovery"):
            try:
                with self.webdriver_service.get_driver() as driver:
                    if self.verbose:
                        print(f"🔍 Navigating to {self.BASE_URL}")
                    
                    driver.get(self.BASE_URL)
                    time.sleep(3)  # Allow page to load
                    
                    return self._extract_faculties_from_page(driver)
                    
            except Exception as e:
                raise ScrapingError(f"Failed to discover faculties: {e}")
    
    def discover_majors_for_faculty(self, faculty_key: str) -> Dict[str, Dict[str, Any]]:
        """
        Discover majors for a specific faculty.
        
        Args:
            faculty_key: Faculty identifier key
            
        Returns:
            Dictionary mapping major keys to major information
            
        Raises:
            ScrapingError: If discovery fails
        """
        with PerformanceTimer(f"Major discovery for {faculty_key}"):
            try:
                with self.webdriver_service.get_driver() as driver:
                    driver.get(self.BASE_URL)
                    time.sleep(3)
                    
                    return self._extract_majors_for_faculty(driver, faculty_key)
                    
            except Exception as e:
                raise ScrapingError(f"Failed to discover majors for {faculty_key}: {e}")
    
    def discover_all_faculties_and_majors(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover all faculties and their majors in one efficient operation.
        
        Returns:
            Complete faculty/major structure
            
        Raises:
            ScrapingError: If discovery fails
        """
        with PerformanceTimer("Complete faculty/major discovery"):
            try:
                with self.webdriver_service.get_driver() as driver:
                    if self.verbose:
                        print(f"🔍 Discovering all faculties and majors from {self.BASE_URL}")
                    
                    driver.get(self.BASE_URL)
                    time.sleep(3)
                    
                    return self._extract_complete_structure(driver)
                    
            except Exception as e:
                raise ScrapingError(f"Failed to discover faculties and majors: {e}")
    
    def _extract_faculties_from_page(self, driver) -> Dict[str, Dict[str, Any]]:
        """Extract faculty information from the main divisions page."""
        faculties = {}
        
        try:
            # Find the main navigation structure
            main_items = self.webdriver_service.safe_find_elements(
                driver, By.XPATH, "/html/body/div[1]/div/div[2]/div/ul/li"
            )
            
            if self.verbose:
                print(f"📋 Found {len(main_items)} main navigation items")
            
            for main_item in main_items:
                try:
                    # Look for faculty sublists within this main item
                    faculty_sublists = self.webdriver_service.safe_find_elements(
                        main_item, By.XPATH, "./ul"
                    )
                    
                    for faculty_sublist in faculty_sublists:
                        faculty_links = self.webdriver_service.safe_find_elements(
                            faculty_sublist, By.XPATH, "./li/a"
                        )
                        
                        for faculty_link in faculty_links:
                            faculty_info = self._extract_faculty_info(faculty_link)
                            if faculty_info:
                                faculties[faculty_info['key']] = faculty_info['data']
                                
                except Exception as e:
                    if self.verbose:
                        print(f"⚠️  Warning: Error processing main item: {e}")
                    continue
            
            if self.verbose:
                print(f"✅ Discovered {len(faculties)} faculties")
            
            return faculties
            
        except Exception as e:
            raise ScrapingError(f"Failed to extract faculties: {e}")
    
    def _extract_majors_for_faculty(self, driver, target_faculty_key: str) -> Dict[str, Dict[str, Any]]:
        """Extract majors for a specific faculty."""
        majors = {}
        
        try:
            # Find the faculty and its majors
            main_items = self.webdriver_service.safe_find_elements(
                driver, By.XPATH, "/html/body/div[1]/div/div[2]/div/ul/li"
            )
            
            for main_item in main_items:
                faculty_sublists = self.webdriver_service.safe_find_elements(
                    main_item, By.XPATH, "./ul"
                )
                
                for faculty_sublist in faculty_sublists:
                    faculty_links = self.webdriver_service.safe_find_elements(
                        faculty_sublist, By.XPATH, "./li/a"
                    )
                    
                    for faculty_link in faculty_links:
                        faculty_name = self.webdriver_service.safe_get_text(faculty_link)
                        faculty_key = TextSanitizer.clean_name_for_key(faculty_name)
                        
                        if faculty_key == target_faculty_key:
                            # Found target faculty, extract its majors
                            majors = self._extract_majors_from_faculty_element(faculty_link)
                            break
            
            if self.verbose:
                print(f"✅ Found {len(majors)} majors for {target_faculty_key}")
            
            return majors
            
        except Exception as e:
            raise ScrapingError(f"Failed to extract majors for {target_faculty_key}: {e}")
    
    def _extract_complete_structure(self, driver) -> Dict[str, Dict[str, Any]]:
        """Extract complete faculty/major structure efficiently."""
        faculties_and_majors = {}
        
        try:
            main_items = self.webdriver_service.safe_find_elements(
                driver, By.XPATH, "/html/body/div[1]/div/div[2]/div/ul/li"
            )
            
            if self.verbose:
                print(f"📋 Processing {len(main_items)} main sections")
            
            for main_item in main_items:
                faculty_sublists = self.webdriver_service.safe_find_elements(
                    main_item, By.XPATH, "./ul"
                )
                
                for faculty_sublist in faculty_sublists:
                    faculty_links = self.webdriver_service.safe_find_elements(
                        faculty_sublist, By.XPATH, "./li/a"
                    )
                    
                    for faculty_link in faculty_links:
                        faculty_info = self._extract_faculty_info(faculty_link)
                        if faculty_info:
                            faculty_key = faculty_info['key']
                            faculty_data = faculty_info['data']
                            
                            # Initialize faculty with proper structure
                            if faculty_key not in faculties_and_majors:
                                faculties_and_majors[faculty_key] = {
                                    'name': faculty_data['name'],
                                    'url': faculty_data['url'],
                                    'majors': {}
                                }
                            
                            # Extract majors for this faculty
                            majors = self._extract_majors_from_faculty_element(faculty_link)
                            faculties_and_majors[faculty_key]['majors'].update(majors)
                            
                            if self.verbose and majors:
                                print(f"  📁 {faculty_data['name']}: {len(majors)} majors")
            
            if self.verbose:
                total_faculties = len(faculties_and_majors)
                total_majors = sum(len(faculty_data.get('majors', {})) for faculty_data in faculties_and_majors.values())
                print(f"✅ Discovery complete: {total_faculties} faculties, {total_majors} majors")
            
            return faculties_and_majors
            
        except Exception as e:
            raise ScrapingError(f"Failed to extract complete structure: {e}")
    
    def _extract_faculty_info(self, faculty_link) -> Optional[Dict[str, Any]]:
        """Extract faculty information from link element."""
        try:
            faculty_name = self.webdriver_service.safe_get_text(faculty_link)
            faculty_url = self.webdriver_service.safe_get_attribute(faculty_link, 'href')
            
            if faculty_name and faculty_url and 'divisions' in faculty_url:
                faculty_key = TextSanitizer.clean_name_for_key(faculty_name)
                
                return {
                    'key': faculty_key,
                    'data': {
                        'name': faculty_name,
                        'url': faculty_url
                    }
                }
            
            return None
            
        except Exception:
            return None
    
    def _extract_majors_from_faculty_element(self, faculty_link) -> Dict[str, Dict[str, Any]]:
        """Extract majors from a faculty link element."""
        majors = {}
        
        try:
            # Get the parent li element of the faculty link
            faculty_li = faculty_link.find_element(By.XPATH, "./..")
            
            # Look for major sublists within this faculty
            major_sublists = self.webdriver_service.safe_find_elements(
                faculty_li, By.XPATH, "./ul"
            )
            
            for major_sublist in major_sublists:
                major_links = self.webdriver_service.safe_find_elements(
                    major_sublist, By.XPATH, "./li/a"
                )
                
                for major_link in major_links:
                    major_info = self._extract_major_info(major_link)
                    if major_info:
                        majors[major_info['key']] = major_info['data']
            
            return majors
            
        except Exception:
            return {}
    
    def _extract_major_info(self, major_link) -> Optional[Dict[str, Any]]:
        """Extract major information from link element."""
        try:
            major_name = self.webdriver_service.safe_get_text(major_link)
            major_url = self.webdriver_service.safe_get_attribute(major_link, 'href')
            
            if major_name and major_url and 'divisions' in major_url:
                major_key = TextSanitizer.clean_name_for_key(major_name)
                
                return {
                    'key': major_key,
                    'data': {
                        'name': major_name,
                        'url': major_url
                    }
                }
            
            return None
            
        except Exception:
            return None
    
    def update_config_with_discovered_data(self, config: ApplicationConfig) -> ApplicationConfig:
        """
        Update configuration with freshly discovered faculty/major data.
        
        Args:
            config: Current configuration object
            
        Returns:
            Updated configuration object
        """
        try:
            if self.verbose:
                print("🔄 Updating configuration with discovered data...")
            
            # Discover all faculties and majors
            discovered_data = self.discover_all_faculties_and_majors()
            
            if discovered_data:
                # Convert discovery format to config format
                config_faculties = {}
                
                for faculty_key, faculty_data in discovered_data.items():
                    # Get faculty info from the discovery data
                    faculty_display_name = faculty_data.get('name', faculty_key.replace('-', ' ').title())
                    
                    # Convert majors to the expected format
                    config_majors = {}
                    majors_dict = faculty_data.get('majors', {})
                    for major_key, major_info in majors_dict.items():
                        config_majors[major_key] = {
                            'display_name': major_info.get('name', major_key.replace('-', ' ').title()),
                            'url': major_info.get('url', '')
                        }
                    
                    config_faculties[faculty_key] = {
                        'display_name': faculty_display_name,
                        'majors': config_majors
                    }
                
                # Update the configuration
                config.faculties = config_faculties
                
                if self.verbose:
                    total_faculties = len(config_faculties)
                    total_majors = sum(len(faculty_data['majors']) for faculty_data in config_faculties.values())
                    print(f"✅ Configuration updated with {total_faculties} faculties and {total_majors} majors")
            else:
                if self.verbose:
                    print("⚠️  No data discovered, keeping existing configuration")
            
            return config
            
        except Exception as e:
            raise ScrapingError(f"Failed to update configuration with discovered data: {e}")
    
    def discover_faculties_and_majors(self) -> Dict[str, Dict[str, Any]]:
        """
        Alias for discover_all_faculties_and_majors for backward compatibility.
        
        Returns:
            Complete faculty/major structure
        """
        return self.discover_all_faculties_and_majors()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if hasattr(self, 'webdriver_service'):
            self.webdriver_service._cleanup()


def get_faculty_display_name(faculties: Dict[str, Any], faculty_key: str) -> str:
    """
    Get display name for a faculty.
    
    Args:
        faculties: Faculty configuration dictionary
        faculty_key: Faculty key
        
    Returns:
        Faculty display name
    """
    faculty_data = faculties.get(faculty_key, {})
    
    if isinstance(faculty_data, dict) and 'display_name' in faculty_data:
        return faculty_data['display_name']
    else:
        return faculty_key.replace('-', ' ').title()


def get_major_display_name(major_key: str, major_data: Any = None) -> str:
    """
    Get display name for a major.
    
    Args:
        major_key: Major key
        major_data: Major data dictionary (optional)
        
    Returns:
        Major display name
    """
    if isinstance(major_data, dict) and 'display_name' in major_data:
        return major_data['display_name']
    else:
        return major_key.replace('-', ' ').title()
