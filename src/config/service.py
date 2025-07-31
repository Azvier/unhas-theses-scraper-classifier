"""
Refactored configuration management with improved separation of concerns.

This module provides a clean, SOLID-compliant configuration system with
proper validation, serialization, and error handling.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from rich.console import Console

from ..core.abstractions import IConfigurationService, ValidationError, ConfigurationError
from ..core.utils import ConfigurationValidator

# Load environment variables
load_dotenv()

console = Console()


@dataclass
class ClassificationConfig:
    """Configuration for thesis classification."""
    batch_size: int = 20
    retries: int = 3
    categories: Dict[str, str] = field(default_factory=dict)
    user_defined_categories: bool = False


@dataclass 
class ScrapingConfig:
    """Configuration for web scraping."""
    headless_browser: bool = True
    delay: float = 1.0
    target_faculty: str = ""
    target_major: str = ""


@dataclass
class ProcessingConfig:
    """Configuration for data processing."""
    enable_excel_export: bool = True
    enable_simplified_json: bool = True
    output_dir: str = "output"


@dataclass
class APIConfig:
    """Configuration for external APIs."""
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"


@dataclass
class ApplicationConfig:
    """Main application configuration."""
    api: APIConfig = field(default_factory=APIConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    # Faculty/major data (auto-populated by discovery)
    faculties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Global settings
    enable_dynamic_discovery: bool = True
    verbose_logging: bool = False

    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Expand environment variables in API key
        if self.api.google_api_key.startswith("${") and self.api.google_api_key.endswith("}"):
            env_var = self.api.google_api_key[2:-1]
            self.api.google_api_key = os.getenv(env_var, "")
        
        # Set default classification categories if empty
        if not self.classification.categories:
            self.classification.categories = {
                "Teori": "Penelitian yang fokus pada pengembangan teori dan konsep fundamental.",
                "Aplikasi": "Penelitian yang fokus pada penerapan teori untuk memecahkan masalah praktis.",
                "Eksperimental": "Penelitian yang melibatkan eksperimen dan pengujian empiris.",
                "Komputasi": "Penelitian yang menggunakan metode komputasi dan simulasi.",
                "Analisis Data": "Penelitian yang fokus pada analisis dan interpretasi data.",
                "Lainnya": "Kategori untuk penelitian yang tidak termasuk dalam kategori lain."
            }


class ConfigurationService(IConfigurationService):
    """Service for managing application configuration."""
    
    def __init__(self):
        self.console = Console()
    
    def load_config(self, config_path: str) -> ApplicationConfig:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Loaded configuration object
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        try:
            if not os.path.exists(config_path):
                self.console.print(f"[yellow]⚠️  Config file not found: {config_path}[/yellow]")
                self.console.print("[yellow]Creating default configuration...[/yellow]")
                create_default_config_file(config_path)
                self.console.print(f"[green]✅ Created default configuration: {config_path}[/green]")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f) or {}
            
            # Expand environment variables
            raw_config = self._expand_env_vars(raw_config)
            
            # Convert flat structure to nested configuration
            config = self._convert_to_config_object(raw_config)
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax in {config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def save_config(self, config: ApplicationConfig, config_path: str) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config: Configuration object to save
            config_path: Path to save configuration file
        """
        try:
            # Convert config object to dictionary
            config_dict = self._convert_to_dict(config)
            
            # Write to file with custom formatting
            with open(config_path, 'w', encoding='utf-8') as f:
                self._write_formatted_yaml(f, config_dict)
                
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def validate_config(self, config: ApplicationConfig) -> bool:
        """
        Validate configuration object.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If configuration is invalid
        """
        errors = []
        
        # Validate API configuration
        if not config.api.google_api_key:
            errors.append("Google API key is required")
        
        # Validate classification categories
        if not config.classification.categories:
            errors.append("Classification categories are required")
        
        # Validate category names for YAML compatibility
        invalid_categories = ConfigurationValidator.validate_category_names(
            config.classification.categories
        )
        if invalid_categories:
            errors.append(f"Invalid category names found: {list(invalid_categories.keys())}")
        
        # Validate paths
        if not config.processing.output_dir:
            errors.append("Output directory is required")
        
        if errors:
            raise ValidationError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
        
        return True
    
    def _expand_env_vars(self, data: Any) -> Any:
        """Recursively expand environment variables in configuration."""
        if isinstance(data, dict):
            return {key: self._expand_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._expand_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, "")
        else:
            return data
    
    def _convert_to_config_object(self, raw_config: Dict[str, Any]) -> ApplicationConfig:
        """Convert raw configuration dictionary to structured config object."""
        # API configuration
        api_config = APIConfig(
            google_api_key=raw_config.get('google_api_key', ''),
            gemini_model=raw_config.get('gemini_model', 'gemini-2.5-pro')
        )
        
        # Scraping configuration
        scraping_config = ScrapingConfig(
            headless_browser=raw_config.get('headless_browser', True),
            delay=raw_config.get('scraping_delay', 1.0),
            target_faculty=raw_config.get('target_faculty', ''),
            target_major=raw_config.get('target_major', '')
        )
        
        # Classification configuration
        classification_config = ClassificationConfig(
            batch_size=raw_config.get('batch_size', 20),
            retries=raw_config.get('classification_retries', 3),
            categories=raw_config.get('classification_categories', {}),
            user_defined_categories=raw_config.get('user_defined_categories', False)
        )
        
        # Processing configuration
        processing_config = ProcessingConfig(
            enable_excel_export=raw_config.get('enable_excel_export', True),
            enable_simplified_json=raw_config.get('enable_simplified_json', True),
            output_dir=raw_config.get('output_dir', 'output')
        )
        
        # Create main config
        config = ApplicationConfig(
            api=api_config,
            scraping=scraping_config,
            classification=classification_config,
            processing=processing_config,
            faculties=raw_config.get('faculties', {}),
            enable_dynamic_discovery=raw_config.get('enable_dynamic_discovery', True),
            verbose_logging=raw_config.get('verbose_logging', False)
        )
        
        return config
    
    def _convert_to_dict(self, config: ApplicationConfig) -> Dict[str, Any]:
        """Convert configuration object to dictionary for serialization."""
        return {
            # API Settings
            'google_api_key': config.api.google_api_key or '${GOOGLE_API_KEY}',
            'gemini_model': config.api.gemini_model,
            
            # Scraping Settings
            'output_dir': config.processing.output_dir,
            'headless_browser': config.scraping.headless_browser,
            'scraping_delay': config.scraping.delay,
            
            # Classification Settings
            'batch_size': config.classification.batch_size,
            'classification_retries': config.classification.retries,
            'target_major': config.scraping.target_major,
            'target_faculty': config.scraping.target_faculty,
            
            # Processing Settings
            'enable_excel_export': config.processing.enable_excel_export,
            'enable_simplified_json': config.processing.enable_simplified_json,
            'enable_dynamic_discovery': config.enable_dynamic_discovery,
            'user_defined_categories': config.classification.user_defined_categories,
            'verbose_logging': config.verbose_logging,
            
            # Classification Categories
            'classification_categories': config.classification.categories,
            
            # Faculties (auto-generated)
            'faculties': config.faculties
        }
    
    def _write_formatted_yaml(self, file, config_dict: Dict[str, Any]) -> None:
        """Write configuration with custom formatting and comments."""
        file.write("# UNHAS Theses Scraper Configuration\n")
        file.write("# Please review and customize the settings below\n\n")
        
        # API Settings
        file.write("# API Settings\n")
        file.write(f"google_api_key: {config_dict['google_api_key']}  # Set this in your .env file\n")
        file.write(f"gemini_model: {config_dict['gemini_model']}\n\n")
        
        # Scraping Settings
        file.write("# Scraping Settings\n")
        file.write(f"output_dir: {config_dict['output_dir']}\n")
        file.write(f"headless_browser: {config_dict['headless_browser']}\n")
        file.write(f"scraping_delay: {config_dict['scraping_delay']}\n\n")
        
        # Classification Settings
        file.write("# Classification Settings\n")
        file.write(f"batch_size: {config_dict['batch_size']}\n")
        file.write(f"classification_retries: {config_dict['classification_retries']}\n")
        file.write(f"target_major: \"{config_dict['target_major']}\"\n")
        file.write(f"target_faculty: \"{config_dict['target_faculty']}\"\n\n")
        
        # Processing Settings
        file.write("# Processing Settings\n")
        file.write(f"enable_excel_export: {config_dict['enable_excel_export']}\n")
        file.write(f"enable_simplified_json: {config_dict['enable_simplified_json']}\n")
        file.write(f"enable_dynamic_discovery: {config_dict['enable_dynamic_discovery']}\n")
        file.write(f"user_defined_categories: {config_dict['user_defined_categories']}\n")
        file.write(f"verbose_logging: {config_dict['verbose_logging']}\n\n")
        
        # Classification Categories
        file.write("# Classification Categories\n")
        file.write("classification_categories:\n")
        for category, description in config_dict['classification_categories'].items():
            if '\n' in description:
                file.write(f"  {category}: |\n")
                for line in description.split('\n'):
                    file.write(f"    {line}\n")
            else:
                file.write(f"  {category}: {description}\n")
        
        file.write("\n# NOTE: Please customize these categories for your research domain!\n")
        file.write("# Make sure distinctions between categories are clear to prevent misclassification.\n\n")
        
        # Auto-generated section separator
        file.write("#" + "="*70 + "\n")
        file.write("# AUTO-GENERATED CONTENT - DO NOT EDIT MANUALLY\n")
        file.write("# The following section is populated by dynamic discovery\n")
        file.write("# Use 'pdm run python main.py discover' to update\n")
        file.write("#" + "="*70 + "\n\n")
        
        # Faculties section
        file.write("faculties:\n")
        if config_dict['faculties']:
            for faculty_key, faculty_data in config_dict['faculties'].items():
                file.write(f"  {faculty_key}:\n")
                # Handle both 'display_name' and 'name' fields
                display_name = faculty_data.get('display_name') or faculty_data.get('name', faculty_key.replace('-', ' ').title())
                file.write(f"    display_name: {display_name}\n")
                file.write("    majors:\n")
                if 'majors' in faculty_data and faculty_data['majors']:
                    for major_key, major_data in faculty_data['majors'].items():
                        file.write(f"      {major_key}:\n")
                        # Handle both 'display_name' and 'name' fields for majors too
                        major_display_name = major_data.get('display_name') or major_data.get('name', major_key.replace('-', ' ').title())
                        file.write(f"        display_name: {major_display_name}\n")
                        if 'url' in major_data:
                            file.write(f"        url: {major_data['url']}\n")
                else:
                    file.write("      {}\n")
        else:
            file.write("  # Will be populated by discovery\n")


def create_default_config_file(output_path: str = "config.yaml") -> None:
    """
    Create a default configuration file.
    
    Args:
        output_path: Path where to create the config file
    """
    config_service = ConfigurationService()
    default_config = ApplicationConfig()
    config_service.save_config(default_config, output_path)
    
    console.print(f"[green]✅ Created default configuration: {output_path}[/green]")
    console.print("[cyan]💡 Next steps:[/cyan]")
    console.print("  1. Set your GOOGLE_API_KEY in a .env file")
    console.print("  2. Run 'python main.py discover' to populate faculty data")
    console.print("  3. Customize classification categories for your domain")


def load_config(config_path: Optional[str] = None, validate: bool = True) -> ApplicationConfig:
    """
    Load configuration from file.
    
    Args:
        config_path: Path to configuration file
        validate: Whether to validate the loaded configuration
        
    Returns:
        Loaded configuration object
    """
    if config_path is None:
        config_path = "config.yaml"
    
    config_service = ConfigurationService()
    config = config_service.load_config(config_path)
    
    if validate:
        config_service.validate_config(config)
    
    return config
