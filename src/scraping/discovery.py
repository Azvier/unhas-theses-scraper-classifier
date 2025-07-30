"""
Dynamic discovery of UNHAS faculties and majors from the repository website.
"""

import time
import os
from typing import Dict
from contextlib import contextmanager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import Config


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


class UNHASRepositoryDiscovery:
    """Dynamically discover faculties and majors from UNHAS repository."""
    
    def __init__(self, headless: bool = True, verbose: bool = False):
        self.base_url = "https://repository.unhas.ac.id/view/divisions/divisions/"
        self.headless = headless
        self.verbose = verbose
        self.driver = None
    
    def _init_driver(self):
        """Initialize the Chrome driver."""
        import logging
        
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
        if self.headless:
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
        options.add_argument("--disable-dev-shm-usage")
        
        # Add unique user data directory to prevent session conflicts
        import tempfile
        import uuid
        temp_dir = tempfile.gettempdir()
        user_data_dir = os.path.join(temp_dir, f"chrome_unhas_scraper_{uuid.uuid4().hex[:8]}")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Create driver with suppressed output
        with suppress_output():
            self.driver = webdriver.Chrome(service=service, options=options)
    
    def _close_driver(self):
        """Close the Chrome driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def discover_faculties(self) -> Dict[str, str]:
        """
        Discover all faculties from the UNHAS repository.
        
        Returns:
            Dict mapping faculty names to their URLs
        """
        if not self.driver:
            self._init_driver()
        
        if self.verbose:
            print("🔍 Discovering faculties from UNHAS repository...")
        self.driver.get(self.base_url)
        time.sleep(3)
        
        faculties = {}
        
        try:
            # Get all faculty list items
            faculty_items = self.driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div/div[2]/div/ul/li")
            
            for i, faculty_item in enumerate(faculty_items, 1):
                try:
                    # Try to find faculty links within this item
                    faculty_links = faculty_item.find_elements(By.XPATH, "./ul/li/a")
                    
                    for link_element in faculty_links:
                        faculty_name = link_element.text.strip()
                        faculty_url = link_element.get_attribute('href')
                        
                        if faculty_name and faculty_url:
                            # Clean up faculty name for use as key
                            faculty_key = self._clean_name(faculty_name)
                            faculties[faculty_key] = {
                                'name': faculty_name,
                                'url': faculty_url
                            }
                            if self.verbose:
                                print(f"  Found faculty: {faculty_name}")
                
                except Exception as e:
                    if self.verbose:
                        print(f"  Warning: Error processing faculty item {i}: {e}")
                    continue
        
        except Exception as e:
            print(f"Error discovering faculties: {e}")
            return {}
        
        if self.verbose:
            print(f"✅ Discovered {len(faculties)} faculties")
        return faculties
    
    def discover_majors_for_faculty(self, faculty_url: str, faculty_name: str) -> Dict[str, str]:
        """
        Discover all majors for a specific faculty.
        
        Args:
            faculty_url: URL of the faculty page
            faculty_name: Name of the faculty for logging
            
        Returns:
            Dict mapping major names to their URLs
        """
        if not self.driver:
            self._init_driver()
        
        if self.verbose:
            print(f"🔍 Discovering majors for {faculty_name}...")
        self.driver.get(faculty_url)
        time.sleep(2)
        
        majors = {}
        
        try:
            # Look for major links in the faculty page
            # Based on your xpath pattern: /html/body/div[1]/div/div[2]/div/div[2]/div/ul/li/ul/li/ul[1]/li/a
            major_elements = self.driver.find_elements(By.XPATH, 
                "/html/body/div[1]/div/div[2]/div/div[2]/div/ul/li/ul/li/ul//li/a")
            
            for major_element in major_elements:
                try:
                    major_name = major_element.text.strip()
                    major_url = major_element.get_attribute('href')
                    
                    if major_name and major_url and 'divisions' in major_url:
                        # Clean up major name for use as key
                        major_key = self._clean_name(major_name)
                        majors[major_key] = {
                            'name': major_name,
                            'url': major_url
                        }
                        if self.verbose:
                            print(f"  Found major: {major_name}")
                
                except Exception as e:
                    if self.verbose:
                        print(f"  Warning: Error processing major element: {e}")
                    continue
        
        except Exception as e:
            print(f"Error discovering majors for {faculty_name}: {e}")
            return {}
        
        if self.verbose:
            print(f"✅ Discovered {len(majors)} majors for {faculty_name}")
        return majors
    
    def discover_all_faculties_and_majors(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Discover all faculties and their majors.
        
        Returns:
            Nested dict: {faculty_key: {major_key: {'name': str, 'url': str}}}
        """
        try:
            self._init_driver()
            
            # First discover all faculties
            faculties = self.discover_faculties()
            
            if not faculties:
                print("❌ No faculties discovered")
                return {}
            
            # Then discover majors for each faculty
            full_structure = {}
            
            for faculty_key, faculty_info in faculties.items():
                faculty_name = faculty_info['name']
                faculty_url = faculty_info['url']
                
                majors = self.discover_majors_for_faculty(faculty_url, faculty_name)
                
                if majors:
                    full_structure[faculty_key] = majors
                else:
                    print(f"⚠️  No majors found for {faculty_name}")
            
            return full_structure
        
        finally:
            self._close_driver()

    def discover_majors_for_faculty_on_demand(self, config: Config, faculty_key: str) -> Config:
        """
        Discover majors for a specific faculty on-demand and update the config.
        
        Args:
            config: Configuration object to update
            faculty_key: The key of the faculty to discover majors for
            
        Returns:
            Updated configuration object
        """
        if faculty_key not in config.faculties:
            print(f"❌ Faculty '{faculty_key}' not found in configuration")
            return config
            
        faculty_data = config.faculties[faculty_key]
        
        # Check if majors are already discovered
        if faculty_data.get('majors') and len(faculty_data['majors']) > 0:
            if self.verbose:
                print(f"✅ Majors for {faculty_data['display_name']} already discovered")
            return config
            
        print(f"🔍 Discovering majors for {faculty_data['display_name']}...")
        
        try:
            # Get faculty URL from the divisions page
            faculties_info = self.discover_faculties()
            
            # Find the faculty by matching display name since keys might be different
            target_faculty_name = faculty_data['display_name']
            matching_faculty = None
            
            for discovered_key, discovered_info in faculties_info.items():
                if discovered_info['name'] == target_faculty_name:
                    matching_faculty = discovered_info
                    break
            
            if matching_faculty:
                faculty_url = matching_faculty['url']
                faculty_name = matching_faculty['name']
                
                # Discover majors for this faculty
                majors = self.discover_majors_for_faculty(faculty_url, faculty_name)
                
                if majors:
                    # Update the configuration with discovered majors
                    config.faculties[faculty_key]['majors'] = {}
                    for major_key, major_info in majors.items():
                        config.faculties[faculty_key]['majors'][major_key] = {
                            'display_name': major_info['name'],
                            'url': major_info['url']
                        }
                    
                    print(f"✅ Discovered {len(majors)} majors for {faculty_name}")
                else:
                    if self.verbose:
                        print(f"⚠️  No majors found for {faculty_name}")
            else:
                print(f"❌ Faculty information not found for '{target_faculty_name}'")
                if self.verbose:
                    print("Available faculties from discovery:")
                    for key, info in faculties_info.items():
                        print(f"  - {info['name']} (key: {key})")
                
        except Exception as e:
            print(f"❌ Error discovering majors for {faculty_key}: {e}")
            
        return config
    
    def _clean_name(self, name: str) -> str:
        """Clean up name to create a valid key."""
        # Remove extra spaces, convert to lowercase, replace spaces with hyphens
        cleaned = name.strip().lower()
        cleaned = cleaned.replace(' ', '-')
        cleaned = cleaned.replace('/', '-')
        cleaned = cleaned.replace('&', 'dan')
        
        # Remove any characters that might cause issues
        import re
        cleaned = re.sub(r'[^\w\-]', '', cleaned)
        
        return cleaned
    
    def update_config_with_discovered_data(self, config: Config) -> Config:
        """
        Update a configuration object with discovered faculty data only.
        Majors will be discovered on-demand when needed.
        
        Args:
            config: Configuration object to update
            
        Returns:
            Updated configuration object
        """
        if self.verbose:
            print("🔄 Updating configuration with discovered faculty data...")
        
        # Only discover faculties initially
        faculties_info = self.discover_faculties()
        
        if faculties_info:
            # Convert to the format expected by Config, with empty majors initially
            config_faculties = {}
            
            for faculty_key, faculty_info in faculties_info.items():
                config_faculties[faculty_key] = {
                    'display_name': faculty_info['name'],
                    'majors': {}  # Empty initially, will be populated on-demand
                }
            
            # Update the configuration
            config.faculties = config_faculties
            
            print(f"✅ Configuration updated with {len(config_faculties)} faculties")
            
            # Also update the classification categories to be user-configurable
            if not hasattr(config, 'user_defined_categories') or not config.user_defined_categories:
                config.classification_categories = {
                    "default": {
                        "Teori": "Penelitian yang fokus pada pengembangan teori dan konsep fundamental.",
                        "Aplikasi": "Penelitian yang fokus pada penerapan teori untuk memecahkan masalah praktis.",
                        "Eksperimental": "Penelitian yang melibatkan eksperimen dan pengujian empiris.",
                        "Komputasi": "Penelitian yang menggunakan metode komputasi dan simulasi.",
                        "Analisis Data": "Penelitian yang fokus pada analisis dan interpretasi data.",
                        "Lainnya": "Kategori untuk penelitian yang tidak termasuk dalam kategori lain."
                    }
                }
        else:
            if self.verbose:
                print("⚠️  No data discovered, keeping existing configuration")
        
        return config


def get_faculty_display_name(faculties_dict: Dict, faculty_key: str) -> str:
    """Get the display name for a faculty from the configuration."""
    if faculty_key in faculties_dict:
        faculty_data = faculties_dict[faculty_key]
        
        # Check if we have the new nested structure with display_name
        if isinstance(faculty_data, dict) and 'display_name' in faculty_data:
            return faculty_data['display_name']
        
        # Check if we have discovery data with name/url structure in majors
        elif isinstance(faculty_data, dict) and 'majors' in faculty_data:
            # For the nested structure, use title case of the key as fallback
            return faculty_key.replace('_', ' ').replace('-', ' ').title()
        
        # Old flat structure - check if values are dicts with name/url
        elif isinstance(faculty_data, dict) and faculty_data:
            first_value = list(faculty_data.values())[0]
            if isinstance(first_value, dict):
                # This is discovery format with name/url structure
                return faculty_key.replace('-', ' ').title()
            else:
                # This is simple URL format, use the key
                return faculty_key.replace('-', ' ').upper()
    
    # Fallback to title case
    return faculty_key.replace('_', ' ').replace('-', ' ').title()


def get_major_display_name(major_key: str) -> str:
    """Get the display name for a major."""
    return major_key.replace('-', ' ').title()


def resolve_faculty_name_to_key(faculties_dict: Dict, input_name: str) -> str:
    """
    Resolve a faculty input name (display name or key) to the configuration key.
    
    Args:
        faculties_dict: Dictionary of faculty configurations
        input_name: User input (can be display name like "Fakultas Teknik" or key like "fakultas-teknik")
        
    Returns:
        The configuration key (e.g., "fakultas-teknik")
        
    Raises:
        ValueError: If no matching faculty is found
    """
    # First try exact key match
    if input_name in faculties_dict:
        return input_name
    
    # Try case-insensitive key match
    input_lower = input_name.lower()
    for faculty_key in faculties_dict.keys():
        if faculty_key.lower() == input_lower:
            return faculty_key
    
    # Try display name match (both stored and generated)
    for faculty_key, faculty_data in faculties_dict.items():
        # Check stored display name
        if isinstance(faculty_data, dict) and 'display_name' in faculty_data:
            if faculty_data['display_name'].lower() == input_name.lower():
                return faculty_key
        
        # Check generated display name
        generated_display = get_faculty_display_name(faculties_dict, faculty_key)
        if generated_display.lower() == input_name.lower():
            return faculty_key
    
    # No match found
    available_faculties = []
    for faculty_key in faculties_dict.keys():
        display_name = get_faculty_display_name(faculties_dict, faculty_key)
        available_faculties.append(f"{display_name} ({faculty_key})")
    
    raise ValueError(f"Invalid faculty '{input_name}'. Available faculties:\n" + "\n".join([f"  • {f}" for f in available_faculties]))


def resolve_major_name_to_key(majors_dict: Dict, input_name: str) -> str:
    """
    Resolve a major input name (display name or key) to the configuration key.
    
    Args:
        majors_dict: Dictionary of major configurations  
        input_name: User input (can be display name like "Teknik Elektro" or key like "teknik-elektro")
        
    Returns:
        The configuration key (e.g., "teknik-elektro")
        
    Raises:
        ValueError: If no matching major is found
    """
    # First try exact key match
    if input_name in majors_dict:
        return input_name
    
    # Try case-insensitive key match
    input_lower = input_name.lower()
    for major_key in majors_dict.keys():
        if major_key.lower() == input_lower:
            return major_key
    
    # Try display name match (both stored and generated)
    for major_key, major_data in majors_dict.items():
        # Check stored display name
        if isinstance(major_data, dict) and 'display_name' in major_data:
            if major_data['display_name'].lower() == input_name.lower():
                return major_key
        
        # Check generated display name
        generated_display = get_major_display_name(major_key)
        if generated_display.lower() == input_name.lower():
            return major_key
    
    # No match found
    available_majors = []
    for major_key in majors_dict.keys():
        if isinstance(majors_dict[major_key], dict) and 'display_name' in majors_dict[major_key]:
            display_name = majors_dict[major_key]['display_name']
        else:
            display_name = get_major_display_name(major_key)
        available_majors.append(f"{display_name} ({major_key})")
    
    raise ValueError(f"Invalid major '{input_name}'. Available majors:\n" + "\n".join([f"  • {m}" for m in available_majors]))
