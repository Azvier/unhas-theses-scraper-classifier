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
        self.base_url = "https://repository.unhas.ac.id/view/divisions/"
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
    
    def discover_faculties_and_majors_from_main_page(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Discover all faculties and their majors from the main divisions page.
        This is more efficient as it gets everything from a single page.
        
        Returns:
            Nested dict: {faculty_key: {major_key: {'name': str, 'url': str}}}
        """
        if not self.driver:
            self._init_driver()

        if self.verbose:
            print("🔍 Discovering faculties and majors from main divisions page...")
        
        self.driver.get(self.base_url)
        time.sleep(3)
        
        faculties_and_majors = {}
        
        try:
            # Get all main list items that contain faculties
            main_list_items = self.driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div/ul/li")
            
            for main_item in main_list_items:
                try:
                    # Look for faculty sublists within this main item
                    faculty_sublists = main_item.find_elements(By.XPATH, "./ul")
                    
                    for faculty_index, faculty_sublist in enumerate(faculty_sublists, 1):
                        # Get faculty link
                        faculty_links = faculty_sublist.find_elements(By.XPATH, "./li/a")
                        
                        for faculty_link in faculty_links:
                            faculty_name = faculty_link.text.strip()
                            faculty_url = faculty_link.get_attribute('href')
                            
                            if faculty_name and faculty_url and 'divisions' in faculty_url:
                                faculty_key = self._clean_name(faculty_name)
                                
                                if self.verbose:
                                    print(f"  📁 Found faculty: {faculty_name}")
                                
                                # Initialize faculty in our structure
                                if faculty_key not in faculties_and_majors:
                                    faculties_and_majors[faculty_key] = {}
                                
                                # Now look for majors under this faculty
                                # Get the parent li element of the faculty link
                                faculty_li = faculty_link.find_element(By.XPATH, "./..")
                                
                                # Look for major sublists within this faculty
                                major_sublists = faculty_li.find_elements(By.XPATH, "./ul")
                                
                                for major_sublist in major_sublists:
                                    major_links = major_sublist.find_elements(By.XPATH, "./li/a")
                                    
                                    for major_link in major_links:
                                        major_name = major_link.text.strip()
                                        major_url = major_link.get_attribute('href')
                                        
                                        if major_name and major_url and 'divisions' in major_url:
                                            major_key = self._clean_name(major_name)
                                            
                                            faculties_and_majors[faculty_key][major_key] = {
                                                'name': major_name,
                                                'url': major_url
                                            }
                                            
                                            if self.verbose:
                                                print(f"    📄 Found major: {major_name}")
                
                except Exception as e:
                    if self.verbose:
                        print(f"  Warning: Error processing main item: {e}")
                    continue
        
        except Exception as e:
            print(f"Error discovering faculties and majors: {e}")
            return {}
        
        total_faculties = len(faculties_and_majors)
        total_majors = sum(len(majors) for majors in faculties_and_majors.values())
        
        if self.verbose:
            print(f"✅ Discovered {total_faculties} faculties with {total_majors} total majors")
        
        return faculties_and_majors

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
            # Use the new XPath pattern you provided
            # Faculty links are at: /html/body/div[1]/div/div[2]/div/ul/li/ul[1]/li/a, etc.
            main_list_items = self.driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div/ul/li")
            
            for main_item in main_list_items:
                try:
                    # Look for faculty sublists within this main item
                    faculty_sublists = main_item.find_elements(By.XPATH, "./ul")
                    
                    for faculty_sublist in faculty_sublists:
                        # Get faculty links
                        faculty_links = faculty_sublist.find_elements(By.XPATH, "./li/a")
                        
                        for faculty_link in faculty_links:
                            faculty_name = faculty_link.text.strip()
                            faculty_url = faculty_link.get_attribute('href')
                            
                            if faculty_name and faculty_url and 'divisions' in faculty_url:
                                faculty_key = self._clean_name(faculty_name)
                                faculties[faculty_key] = {
                                    'name': faculty_name,
                                    'url': faculty_url
                                }
                                if self.verbose:
                                    print(f"  Found faculty: {faculty_name}")
                
                except Exception as e:
                    if self.verbose:
                        print(f"  Warning: Error processing main item: {e}")
                    continue
        
        except Exception as e:
            print(f"Error discovering faculties: {e}")
            return {}
        
        if self.verbose:
            print(f"✅ Discovered {len(faculties)} faculties")
        return faculties

    def discover_majors_for_faculty_from_main_page(self, faculty_name: str) -> Dict[str, str]:
        """
        Discover all majors for a specific faculty from the main divisions page.
        This is more efficient than navigating to individual faculty pages.
        
        Args:
            faculty_name: Name of the faculty to find majors for
            
        Returns:
            Dict mapping major names to their URLs
        """
        if not self.driver:
            self._init_driver()

        if self.verbose:
            print(f"🔍 Discovering majors for {faculty_name} from main divisions page...")
        
        self.driver.get(self.base_url)
        time.sleep(3)
        
        majors = {}
        
        try:
            # Get all main list items
            main_list_items = self.driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div/ul/li")
            
            for main_item in main_list_items:
                try:
                    # Look for faculty sublists within this main item
                    faculty_sublists = main_item.find_elements(By.XPATH, "./ul")
                    
                    for faculty_sublist in faculty_sublists:
                        # Get faculty links
                        faculty_links = faculty_sublist.find_elements(By.XPATH, "./li/a")
                        
                        for faculty_link in faculty_links:
                            current_faculty_name = faculty_link.text.strip()
                            
                            # Check if this is the faculty we're looking for
                            if current_faculty_name.lower() == faculty_name.lower():
                                if self.verbose:
                                    print(f"  📁 Found target faculty: {current_faculty_name}")
                                
                                # Get the parent li element of the faculty link
                                faculty_li = faculty_link.find_element(By.XPATH, "./..")
                                
                                # Look for major sublists within this faculty
                                major_sublists = faculty_li.find_elements(By.XPATH, "./ul")
                                
                                for major_sublist in major_sublists:
                                    major_links = major_sublist.find_elements(By.XPATH, "./li/a")
                                    
                                    for major_link in major_links:
                                        major_name = major_link.text.strip()
                                        major_url = major_link.get_attribute('href')
                                        
                                        if major_name and major_url and 'divisions' in major_url:
                                            major_key = self._clean_name(major_name)
                                            majors[major_key] = {
                                                'name': major_name,
                                                'url': major_url
                                            }
                                            if self.verbose:
                                                print(f"    📄 Found major: {major_name}")
                                
                                # Found the faculty, no need to continue searching
                                if majors:
                                    break
                        
                        if majors:
                            break
                    
                    if majors:
                        break
                
                except Exception as e:
                    if self.verbose:
                        print(f"  Warning: Error processing main item: {e}")
                    continue
        
        except Exception as e:
            print(f"Error discovering majors for {faculty_name}: {e}")
            return {}
        
        if self.verbose:
            print(f"✅ Discovered {len(majors)} majors for {faculty_name}")
        return majors

    def discover_all_faculties_and_majors(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Discover all faculties and their majors efficiently from the main page.
        
        Returns:
            Nested dict: {faculty_key: {major_key: {'name': str, 'url': str}}}
        """
        try:
            self._init_driver()
            
            # Use the new efficient method that gets everything from one page
            full_structure = self.discover_faculties_and_majors_from_main_page()
            
            if not full_structure:
                print("❌ No faculties and majors discovered")
                return {}
            
            return full_structure
        
        finally:
            self._close_driver()

    def discover_majors_for_faculty(self, faculty_url: str, faculty_name: str) -> Dict[str, str]:
        """
        Discover all majors for a specific faculty.
        Now uses the main page method for efficiency.
        
        Args:
            faculty_url: URL of the faculty page (not used in new implementation)
            faculty_name: Name of the faculty for logging
            
        Returns:
            Dict mapping major names to their URLs
        """
        return self.discover_majors_for_faculty_from_main_page(faculty_name)

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
        Update a configuration object with discovered faculty and major data efficiently.
        Now uses the new main page discovery method to get everything at once.
        
        Args:
            config: Configuration object to update
            
        Returns:
            Updated configuration object
        """
        if self.verbose:
            print("🔄 Updating configuration with discovered faculty and major data...")
        
        try:
            self._init_driver()
            
            # Use the new efficient method to get all faculties and majors at once
            faculties_and_majors = self.discover_faculties_and_majors_from_main_page()
            
            if faculties_and_majors:
                # Convert to the format expected by Config
                config_faculties = {}
                
                for faculty_key, majors_dict in faculties_and_majors.items():
                    # Get faculty display name from the first major if available
                    faculty_display_name = faculty_key.replace('-', ' ').title()
                    
                    # Convert majors to the expected format
                    config_majors = {}
                    for major_key, major_info in majors_dict.items():
                        config_majors[major_key] = {
                            'display_name': major_info['name'],
                            'url': major_info['url']
                        }
                    
                    config_faculties[faculty_key] = {
                        'display_name': faculty_display_name,
                        'majors': config_majors
                    }
                
                # Update the configuration
                config.faculties = config_faculties
                
                total_faculties = len(config_faculties)
                total_majors = sum(len(faculty_data['majors']) for faculty_data in config_faculties.values())
                
                print(f"✅ Configuration updated with {total_faculties} faculties and {total_majors} majors")
                
                # Also update the classification categories to be user-configurable
                if not hasattr(config, 'user_defined_categories') or not config.user_defined_categories:
                    config.classification_categories = {
                        "Teori": "Penelitian yang fokus pada pengembangan teori dan konsep fundamental.",
                        "Aplikasi": "Penelitian yang fokus pada penerapan teori untuk memecahkan masalah praktis.",
                        "Eksperimental": "Penelitian yang melibatkan eksperimen dan pengujian empiris.",
                        "Komputasi": "Penelitian yang menggunakan metode komputasi dan simulasi.",
                        "Analisis Data": "Penelitian yang fokus pada analisis dan interpretasi data.",
                        "Lainnya": "Kategori untuk penelitian yang tidak termasuk dalam kategori lain."
                    }
            else:
                if self.verbose:
                    print("⚠️  No data discovered, keeping existing configuration")
            
        finally:
            self._close_driver()
        
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
