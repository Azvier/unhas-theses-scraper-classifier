"""
Utility functions and helpers shared across the application.

This module contains common utility functions that are used by multiple
components to avoid code duplication and provide consistent behavior.
"""

import os
import re
import tempfile
import uuid
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from contextlib import contextmanager

from .abstractions import OperationType


class FileNameExtractor:
    """Utility class for extracting information from filenames."""
    
    @staticmethod
    def extract_faculty_major_from_filename(input_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract faculty and major names from the input filename.
        
        Args:
            input_path: Path to the file
            
        Returns:
            Tuple of (faculty, major) or (None, None) if extraction fails
        """
        try:
            filename = os.path.basename(input_path)
            filename_without_ext = os.path.splitext(filename)[0]
            parts = filename_without_ext.split('_')
            
            if len(parts) >= 3:
                # Handle different filename patterns
                if any(keyword in parts for keyword in ['classified', 'simplified']):
                    return parts[0], parts[1]
                else:
                    return parts[0], parts[1]
                    
        except Exception as e:
            print(f"Warning: Could not extract faculty/major from filename '{input_path}': {e}")
        
        return None, None


class FileNameGenerator:
    """Utility class for generating consistent output filenames."""
    
    @staticmethod
    def generate_filename(operation: OperationType,
                         faculty: str,
                         major: str,
                         timestamp: Optional[str] = None,
                         extension: str = "json") -> str:
        """
        Generate consistent filename for operation output.
        
        Args:
            operation: Type of operation
            faculty: Faculty identifier
            major: Major identifier  
            timestamp: Optional timestamp, current time if None
            extension: File extension without dot
            
        Returns:
            Generated filename
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        operation_suffix = {
            OperationType.SCRAPE: "",
            OperationType.CLASSIFY: "_classified",
            OperationType.EXPORT_EXCEL: "_classified",
            OperationType.SIMPLIFY: "_simplified",
            OperationType.ALL: "_classified"
        }
        
        suffix = operation_suffix.get(operation, "")
        base_name = f"{faculty}_{major}{suffix}_{timestamp}"
        
        return f"{base_name}.{extension}"


class TextSanitizer:
    """Utility class for text sanitization and cleaning."""
    
    # Character replacement mappings for XML/Excel compatibility
    REPLACEMENT_MAP = {
        # Smart quotes
        '\u201c': '"',   # Left double quotation mark
        '\u201d': '"',   # Right double quotation mark
        '\u2018': "'",   # Left single quotation mark  
        '\u2019': "'",   # Right single quotation mark
        # Dashes
        '\u2014': '-',   # Em dash
        '\u2013': '-',   # En dash
        # Mathematical symbols
        '\u00d7': 'x',   # Multiplication sign
        '\u00b1': '+/-', # Plus-minus sign
        '\u2264': '<=',  # Less than or equal to
        '\u2265': '>=',  # Greater than or equal to
        # Greek letters
        '\u03b1': 'alpha', '\u03b2': 'beta', '\u03b3': 'gamma', '\u03b4': 'delta',
        '\u03bb': 'lambda', '\u03bc': 'mu', '\u00b5': 'mu', '\u03c0': 'pi',
        '\u03c3': 'sigma', '\u03a9': 'Omega',
        # Degree and temperature
        '\u00b0': ' deg', '\u2103': 'C', '\u2109': 'F', '\u02da': ' deg',
        # Other problematic characters
        '\u2026': '...'   # Horizontal ellipsis
    }
    
    @classmethod
    def sanitize_xml_text(cls, text: str) -> str:
        """
        Sanitize text to remove characters that are illegal in XML/Excel.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text safe for XML/Excel
        """
        if not isinstance(text, str):
            return text
        
        # Apply character replacements
        sanitized_text = text
        for old_char, new_char in cls.REPLACEMENT_MAP.items():
            sanitized_text = sanitized_text.replace(old_char, new_char)
        
        # Remove XML-illegal control characters (keep tab, LF, CR)
        sanitized_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\uFFFE\uFFFF]', '', sanitized_text)
        
        # Remove surrogate pairs (invalid in XML)
        sanitized_text = re.sub(r'[\uD800-\uDFFF]', '', sanitized_text)
        
        return sanitized_text
    
    @staticmethod
    def clean_name_for_key(name: str) -> str:
        """
        Clean up name to create a valid identifier key.
        
        Args:
            name: Name to clean
            
        Returns:
            Cleaned name suitable for use as key
        """
        cleaned = name.strip().lower()
        cleaned = cleaned.replace(' ', '-')
        cleaned = cleaned.replace('/', '-')
        cleaned = cleaned.replace('&', 'dan')
        
        # Remove any characters that might cause issues
        cleaned = re.sub(r'[^\w\-]', '', cleaned)
        
        return cleaned


class PathManager:
    """Utility class for path management and operations."""
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> None:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory_path: Path to directory
        """
        os.makedirs(directory_path, exist_ok=True)
    
    @staticmethod
    def get_unique_temp_directory() -> str:
        """
        Get a unique temporary directory path.
        
        Returns:
            Path to unique temporary directory
        """
        temp_dir = tempfile.gettempdir()
        unique_id = uuid.uuid4().hex[:8]
        return os.path.join(temp_dir, f"unhas_scraper_{unique_id}")
    
    @staticmethod
    def resolve_output_path(output_dir: str, filename: str) -> str:
        """
        Resolve complete output file path.
        
        Args:
            output_dir: Output directory
            filename: Filename
            
        Returns:
            Complete file path
        """
        PathManager.ensure_directory_exists(output_dir)
        return os.path.join(output_dir, filename)


@contextmanager
def suppress_output():
    """Context manager to suppress stdout and stderr."""
    import sys
    
    if os.name == 'nt':  # Windows
        try:
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


class ConfigurationValidator:
    """Utility class for configuration validation."""
    
    @staticmethod
    def validate_category_names(categories: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and suggest fixes for illegal category names.
        
        Args:
            categories: Dictionary of category names and descriptions
            
        Returns:
            Dictionary of problematic names to suggested fixes
        """
        illegal_chars = [':', '[', ']', '{', '}', '|', '#', '&', '*', '!', '%', '@', '`']
        suggestions = {}
        
        for name in categories.keys():
            has_issues = False
            suggested_name = name
            
            # Check for illegal characters
            for char in illegal_chars:
                if char in name:
                    has_issues = True
                    if char == ':':
                        suggested_name = suggested_name.replace(':', ' -')
                    else:
                        suggested_name = suggested_name.replace(char, '')
            
            # Check for leading dashes
            if name.startswith('-'):
                has_issues = True
                suggested_name = suggested_name.lstrip('-').strip()
            
            if has_issues:
                # Clean up multiple spaces and ensure not empty
                suggested_name = ' '.join(suggested_name.split())
                if not suggested_name:
                    suggested_name = f"Category_{hash(name) % 1000}"
                suggestions[name] = suggested_name
        
        return suggestions
    
    @staticmethod
    def sanitize_category_name(name: str) -> str:
        """
        Sanitize a single category name.
        
        Args:
            name: Category name to sanitize
            
        Returns:
            Sanitized category name
        """
        suggestions = ConfigurationValidator.validate_category_names({name: ""})
        return suggestions.get(name, name)


class PerformanceTimer:
    """Utility class for performance timing."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        duration = end_time - self.start_time
        print(f"✓ {self.operation_name} completed in {duration.total_seconds():.2f} seconds")


def get_display_name_from_key(key: str) -> str:
    """
    Convert a key to display name format.
    
    Args:
        key: Identifier key (e.g., 'fakultas-teknik')
        
    Returns:
        Display name (e.g., 'Fakultas Teknik')
    """
    return key.replace('-', ' ').title()


def resolve_name_to_key(options: Dict[str, Any], input_name: str) -> str:
    """
    Resolve user input name to configuration key.
    
    Args:
        options: Dictionary of available options
        input_name: User input name
        
    Returns:
        Matching configuration key
        
    Raises:
        ValueError: If no matching option found
    """
    # Try exact key match first
    if input_name in options:
        return input_name
    
    # Try display name matching
    for key, data in options.items():
        if isinstance(data, dict) and 'display_name' in data:
            display_name = data['display_name']
        else:
            display_name = get_display_name_from_key(key)
        
        # Case insensitive comparison
        if (input_name.lower() == key.lower() or 
            input_name.lower() == display_name.lower() or
            key.lower().replace(" ", "").replace(".", "") == 
            input_name.lower().replace(" ", "").replace(".", "")):
            return key
    
    # Create helpful error message
    available_names = []
    for key, data in options.items():
        if isinstance(data, dict) and 'display_name' in data:
            available_names.append(f"'{data['display_name']}' (key: {key})")
        else:
            available_names.append(f"'{get_display_name_from_key(key)}' (key: {key})")
    
    raise ValueError(
        f"Unknown option: '{input_name}'. Available options:\n" +
        "\n".join(f"  - {name}" for name in available_names)
    )
