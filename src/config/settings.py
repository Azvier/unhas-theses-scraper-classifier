"""
Configuration management for UNHAS Theses Scraper.
"""

import os
import re
import yaml
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from rich.console import Console
from dotenv import load_dotenv

# Load environment variables from .env file at module level
load_dotenv()

console = Console()


def _expand_env_vars(content: str) -> str:
    """
    Expand environment variables in YAML content.
    Supports ${VAR} and ${VAR:-default} syntax.
    
    Examples:
        ${GOOGLE_API_KEY} -> value of GOOGLE_API_KEY env var or original string if not set
        ${GOOGLE_API_KEY:-default_key} -> value of GOOGLE_API_KEY or "default_key" if not set
    """
    def replace_var(match):
        var_expr = match.group(1)
        if ':-' in var_expr:
            var_name, default_value = var_expr.split(':-', 1)
            return os.getenv(var_name.strip(), default_value.strip())
        else:
            env_value = os.getenv(var_expr.strip())
            # If environment variable is not set, keep the original placeholder
            # This allows the later validation to catch missing required variables
            return env_value if env_value is not None else match.group(0)
    
    # Pattern to match ${VAR} or ${VAR:-default}
    pattern = r'\$\{([^}]+)\}'
    return re.sub(pattern, replace_var, content)


@dataclass
class Config:
    """Configuration class for the UNHAS Theses Scraper."""
    
    # API Settings
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"  # Configurable Gemini model
    
    # Scraping Settings
    output_dir: str = "output"
    headless_browser: bool = True
    scraping_delay: float = 1.0  # Delay between requests in seconds
    
    # Classification Settings
    batch_size: int = 20
    classification_retries: int = 3
    target_major: str = ""  # Will be set by user selection
    target_faculty: str = ""  # Will be set by user selection
    
    # Processing Settings
    enable_excel_export: bool = True
    enable_simplified_json: bool = True
    
    # Dynamic Discovery Settings
    enable_dynamic_discovery: bool = True  # Default to True for better UX
    user_defined_categories: bool = False   # Set to True if user has defined custom categories
    verbose_logging: bool = False  # Set to True for detailed discovery logs
    
    # Classification Categories per Major (moved to top for better visibility)
    classification_categories: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "default": {
            "Teori": "Penelitian yang fokus pada pengembangan teori dan konsep fundamental.",
            "Aplikasi": "Penelitian yang fokus pada penerapan teori untuk memecahkan masalah praktis.",
            "Eksperimental": "Penelitian yang melibatkan eksperimen dan pengujian empiris.",
            "Komputasi": "Penelitian yang menggunakan metode komputasi dan simulasi.",
            "Analisis Data": "Penelitian yang fokus pada analisis dan interpretasi data.",
            "Lainnya": "Kategori untuk penelitian yang tidak termasuk dalam kategori lain."
        }
    })
    
    # Faculty and Major Configuration (auto-populated, should be at bottom)
    faculties: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    def save_config(self, config_path: str = "config.yaml") -> None:
        """Save the current configuration to a YAML file with proper structure."""
        with open(config_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# UNHAS Theses Scraper Configuration\n")
            f.write("# Please review and customize the settings below\n\n")
            
            # API Settings
            f.write("# API Settings\n")
            f.write("google_api_key: ${GOOGLE_API_KEY}  # Set this in your .env file\n")
            f.write(f"gemini_model: {self.gemini_model}\n\n")
            
            # Scraping Settings
            f.write("# Scraping Settings\n")
            f.write(f"output_dir: {self.output_dir}\n")
            f.write(f"headless_browser: {self.headless_browser}\n")
            f.write(f"scraping_delay: {self.scraping_delay}\n\n")
            
            # Classification Settings
            f.write("# Classification Settings\n")
            f.write(f"batch_size: {self.batch_size}\n")
            f.write(f"classification_retries: {self.classification_retries}\n")
            f.write(f"target_major: \"{self.target_major}\"\n")
            f.write(f"target_faculty: \"{self.target_faculty}\"\n\n")
            
            # Processing Settings
            f.write("# Processing Settings\n")
            f.write(f"enable_excel_export: {self.enable_excel_export}\n")
            f.write(f"enable_simplified_json: {self.enable_simplified_json}\n")
            f.write(f"enable_dynamic_discovery: {self.enable_dynamic_discovery}\n")
            f.write(f"user_defined_categories: {self.user_defined_categories}\n")
            f.write(f"verbose_logging: {self.verbose_logging}\n\n")
            
            # Classification Categories
            f.write("# Classification Categories\n")
            f.write("classification_categories:\n")
            for major, categories in self.classification_categories.items():
                f.write(f"  {major}:\n")
                for category, description in categories.items():
                    # Handle multi-line descriptions properly
                    if '\n' in description:
                        f.write(f"    {category}: |\n")
                        for line in description.split('\n'):
                            f.write(f"      {line}\n")
                    else:
                        f.write(f"    {category}: {description}\n")
            f.write("\n# NOTE: Please customize these categories for your research domain!\n")
            f.write("# Make sure distinctions between categories are clear to prevent misclassification.\n")
            f.write("# Below is an example of how you might define categories for classification task for statistics major:\n\n")
            f.write("# classification_categories:\n")
            f.write("#   default:\n")
            f.write("#     Regresi: Fokus pada **inferensi statistik** untuk memahami dan mengukur hubungan antar variabel menggunakan model dengan **bentuk fungsional yang telah ditentukan** (misalnya, linear, logistik). Tujuan utamanya adalah menjelaskan *seberapa besar* pengaruh satu variabel terhadap variabel lain.\n")
            f.write("#     Regresi Nonparametrik: Fokus pada pemodelan hubungan antar variabel **TANPA asumsi bentuk fungsional tertentu**. Metode ini sangat fleksibel dan digunakan ketika pola data kompleks, non-linear, dan tidak diketahui sebelumnya. Tujuannya adalah membiarkan data 'berbicara' untuk membentuk modelnya sendiri.\n")
            f.write("#     Pengendalian Kualitas Statistika: Fokus pada **pemantauan (monitoring) proses yang sedang berjalan** untuk memastikan stabilitas dan konsistensi output. Alat utamanya adalah **peta kendali (control chart)** untuk mendeteksi variasi yang tidak wajar secara visual dan menjaga proses tetap dalam spesifikasi.\n")
            f.write("#     Perancangan Percobaan: Fokus pada **perancangan eksperimen secara proaktif SEBELUM data dikumpulkan**. Tujuannya adalah untuk secara efisien membandingkan efek dari berbagai **perlakuan (treatments)** melalui intervensi aktif untuk menemukan pengaturan atau kondisi yang paling optimal.\n")
            f.write("#     Analisis Runtun Waktu: Fokus pada **analisis data yang variabel utamanya adalah waktu**. Metode ini secara khusus menangani data dengan **ketergantungan temporal** (nilai saat ini dipengaruhi oleh nilai sebelumnya). Tujuan utamanya adalah memahami pola historis dan melakukan **peramalan (forecasting)**.\n")
            f.write("#     Machine Learning: Fokus utama pada **akurasi prediksi**. Tujuannya adalah membangun algoritma yang dapat belajar dari data untuk membuat prediksi atau klasifikasi seakurat mungkin, seringkali **mengorbankan interpretasi model** demi performa prediktif yang superior.\n")
            f.write("#     Analisis Data Spasial: Fokus pada **analisis data yang variabel utamanya adalah lokasi geografis**. Metode ini secara khusus menangani data dengan **ketergantungan spasial** (nilai di satu lokasi dipengaruhi oleh nilai di lokasi tetangganya). Fokus utamanya adalah pemetaan dan pemodelan **autokorelasi spasial**.\n")
            f.write("#     Analisis Survival: Fokus pada **metode statistik khusus untuk menganalisis data 'waktu-ke-kejadian' (time-to-event)**. Fokusnya adalah memodelkan waktu hingga suatu peristiwa terjadi dan menangani **data tersensor (censored data)**, di mana peristiwa tersebut tidak diamati untuk semua subjek.\n")
            f.write("#     Ekonometrika dan Manajemen Risiko: Fokus pada **aplikasi statistik khusus pada data keuangan dan ekonomi** untuk mengukur dan mengelola risiko. Fokus utamanya adalah kuantifikasi risiko investasi melalui metrik seperti **Value at Risk (VaR) dan CVaR**, pemodelan portofolio, dan analisis dependensi aset.\n")
            f.write("#     Lainnya: Fokus pada **kategori untuk metodologi statistik yang tidak memiliki karakteristik unik dari kategori lain yang telah disebutkan**. Contohnya meliputi **psikometri, bioinformatika, atau analisis data kategorik murni**.\n\n")
            
            # Add separator for auto-generated content
            f.write("#" + "="*70 + "\n")
            f.write("# AUTO-GENERATED CONTENT - DO NOT EDIT MANUALLY\n")
            f.write("# The following section is populated by dynamic discovery\n")
            f.write("# Use 'pdm run python main.py discover' to update\n")
            f.write("#" + "="*70 + "\n\n")
            
            # Write faculties section
            f.write("faculties:\n")
            if self.faculties:
                for faculty_key, faculty_data in self.faculties.items():
                    f.write(f"  {faculty_key}:\n")
                    f.write(f"    display_name: {faculty_data['display_name']}\n")
                    f.write("    majors:\n")
                    if 'majors' in faculty_data and faculty_data['majors']:
                        for major_key, major_data in faculty_data['majors'].items():
                            f.write(f"      {major_key}:\n")
                            f.write(f"        display_name: {major_data['display_name']}\n")
                            if 'url' in major_data:
                                f.write(f"        url: {major_data['url']}\n")
                    else:
                        f.write("      {}\n")
            else:
                f.write("  # Will be populated by discovery\n")


def load_config(config_path: Optional[str] = None, validate: bool = True) -> Config:
    """
    Load configuration from YAML file or environment variables.
    
    Args:
        config_path: Path to configuration file. If None, uses default locations.
        validate: Whether to perform validation after loading.
        
    Returns:
        Config object with loaded settings.
    """
    config = Config()
    
    # Try to load from YAML file
    if config_path is None:
        # Try default locations
        possible_paths = [
            "config.yaml",
            "config.yml", 
            os.path.expanduser("~/.unhas-scraper/config.yaml")
        ]
    else:
        possible_paths = [config_path]
    
    config_loaded = False
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                
                # Expand environment variables in YAML content
                expanded_content = _expand_env_vars(raw_content)
                yaml_config = yaml.safe_load(expanded_content)
                
                if yaml_config:
                    _update_config_from_dict(config, yaml_config)
                    config_loaded = True
                    print(f"Configuration loaded from: {path}")
                break
            except Exception as e:
                print(f"Warning: Failed to load config from {path}: {e}")
    
    if not config_loaded:
        print("No configuration file found. Using defaults and environment variables.")
    
    # Final override with environment variables (for backward compatibility)
    if not config.google_api_key or config.google_api_key.startswith("${"):
        config.google_api_key = os.getenv("GOOGLE_API_KEY", "")
    
    # Perform validation if requested
    if validate:
        try:
            validate_config_basic(config)
        except ValueError as e:
            console.print(f"[yellow]⚠️  Configuration validation warning: {e}[/yellow]")
            console.print("[dim]Run 'python main.py validate-config' for detailed validation[/dim]")
    
    return config


def _update_config_from_dict(config: Config, config_dict: Dict[str, Any]):
    """Update config object from dictionary, handling nested structures."""
    for key, value in config_dict.items():
        if hasattr(config, key):
            if isinstance(value, dict) and isinstance(getattr(config, key), dict):
                # Handle nested dictionaries
                current_value = getattr(config, key)
                current_value.update(value)
            else:
                setattr(config, key, value)


def validate_config_basic(config: Config) -> None:
    """
    Perform basic configuration validation without prompts or discovery.
    
    Args:
        config: Configuration object to validate.
        
    Raises:
        ValueError: If configuration is invalid.
    """
    # Directory validation
    if not config.output_dir:
        raise ValueError("Output directory cannot be empty")
    
    # Numeric validations
    if config.batch_size <= 0:
        raise ValueError("Batch size must be positive")
    
    if config.classification_retries < 1:
        raise ValueError("Classification retries must be at least 1")
    
    if config.scraping_delay < 0:
        raise ValueError("Scraping delay cannot be negative")
    
    # Gemini model validation
    if not config.gemini_model:
        raise ValueError("Gemini model cannot be empty")


def validate_config(config: Config) -> None:
    """
    Validate configuration settings with enhanced checks including prompts and discovery.
    
    Args:
        config: Configuration object to validate.
        
    Raises:
        ValueError: If configuration is invalid.
    """
    # First run basic validation
    validate_config_basic(config)
    
    # API Key validation
    if not config.google_api_key:
        raise ValueError(
            "Google API key not configured. Please set GOOGLE_API_KEY environment "
            "variable or add it to your configuration file."
        )
    
    # Check if API key is still a placeholder (environment variable not substituted)
    if config.google_api_key.startswith("${") and config.google_api_key.endswith("}"):
        var_name = config.google_api_key[2:-1]  # Extract variable name from ${VAR}
        raise ValueError(
            f"Environment variable '{var_name}' is not set. Please set it in your .env file "
            f"or environment, or provide the API key directly in the config file."
        )
    
    # Enhanced category validation with user prompts
    config = validate_and_prompt_categories(config)
    
    # Faculty/Major validation (only if faculties are populated and targets are set)
    if config.faculties and config.target_faculty and config.target_major:
        # Resolve faculty display name to technical key
        resolved_faculty_key = resolve_faculty_key(config.faculties, config.target_faculty)
        if not resolved_faculty_key:
            available_faculties = []
            for faculty_key, faculty_data in config.faculties.items():
                if isinstance(faculty_data, dict) and 'display_name' in faculty_data:
                    display_name = faculty_data['display_name']
                    available_faculties.append(f"{display_name} (key: {faculty_key})")
                else:
                    available_faculties.append(faculty_key)
            
            raise ValueError(
                f"Invalid target faculty '{config.target_faculty}'. "
                f"Available faculties:\n  " + "\n  ".join(available_faculties)
            )
        
        # Update config with resolved faculty key
        config.target_faculty = resolved_faculty_key
        faculty_data = config.faculties[resolved_faculty_key]
        
        # Handle new nested structure - if majors haven't been discovered yet, skip major validation
        if isinstance(faculty_data, dict) and 'majors' in faculty_data:
            faculty_majors = faculty_data['majors']
            if faculty_majors and len(faculty_majors) > 0:
                # Resolve major display name to technical key
                resolved_major_key = resolve_major_key(faculty_majors, config.target_major)
                if not resolved_major_key:
                    available_majors = []
                    for major_key, major_data in faculty_majors.items():
                        if isinstance(major_data, dict) and 'display_name' in major_data:
                            display_name = major_data['display_name']
                            available_majors.append(f"{display_name} (key: {major_key})")
                        else:
                            available_majors.append(major_key)
                    
                    raise ValueError(
                        f"Invalid target major '{config.target_major}' for faculty '{config.target_faculty}'. "
                        f"Available majors:\n  " + "\n  ".join(available_majors)
                    )
                
                # Update config with resolved major key
                config.target_major = resolved_major_key
            else:
                # Majors haven't been discovered yet - this is okay for on-demand discovery
                console.print(f"[yellow]⚠️  Note: Majors for '{config.target_faculty}' haven't been discovered yet. Will be discovered on-demand.[/yellow]")
        else:
            # Handle old flat structure
            resolved_major_key = resolve_major_key(faculty_data, config.target_major)
            if not resolved_major_key:
                available_majors = list(faculty_data.keys())
                raise ValueError(
                    f"Invalid target major '{config.target_major}' for faculty '{config.target_faculty}'. "
                    f"Available majors: {', '.join(available_majors)}"
                )
            # Update config with resolved major key
            config.target_major = resolved_major_key
    elif config.faculties and (not config.target_faculty or not config.target_major):
        # Faculties are available but no target is set - inform user
        console.print("\n[yellow]ℹ️  No target faculty/major set in configuration.[/yellow]")
        console.print("[dim]Use interactive mode or set target_faculty and target_major in config.yaml[/dim]")
    elif config.enable_dynamic_discovery:
        console.print("\n[yellow]⚠️  No faculties found in configuration.[/yellow]")
        console.print("[cyan]Running discovery to populate faculty data...[/cyan]")
        try:
            from src.scraping.discovery import UNHASRepositoryDiscovery
            discovery = UNHASRepositoryDiscovery()
            faculties_data = discovery.discover_all_faculties()
            config.faculties = faculties_data
            console.print("[green]✅ Faculty discovery completed![/green]")
            # Save updated config
            config.save_config()
        except Exception as e:
            console.print(f"[red]❌ Discovery failed: {e}[/red]")
            console.print("[yellow]You can manually run: pdm run python main.py discover[/yellow]")
    
    # Classification categories validation
    major_categories = config.classification_categories.get(
        config.target_major, 
        config.classification_categories.get("default", {})
    )
    
    if not major_categories:
        raise ValueError(
            f"No classification categories defined for major '{config.target_major}'"
        )
    
    for category, description in major_categories.items():
        if not description.strip():
            raise ValueError(f"Empty description for category: {category}")


def create_default_config_file(output_path: str = "config.yaml") -> None:
    """
    Create a comprehensive default configuration file with all faculties and proper structure.
    
    Args:
        output_path: Path where to create the configuration file.
    """
    # Create a default config instance with all faculties pre-populated
    config = Config()
    
    # Add all 17 UNHAS faculties with their basic structure
    config.faculties = {
        "fakultas-ekonomi": {
            "display_name": "Fakultas Ekonomi dan Bisnis",
            "majors": {}
        },
        "fakultas-farmasi": {
            "display_name": "Fakultas Farmasi",
            "majors": {}
        },
        "fakultas-hukum": {
            "display_name": "Fakultas Hukum",
            "majors": {}
        },
        "fakultas-ilmu-budaya": {
            "display_name": "Fakultas Ilmu Budaya",
            "majors": {}
        },
        "fakultas-ilmu-kelautan-dan-perikanan": {
            "display_name": "Fakultas Ilmu Kelautan dan Perikanan",
            "majors": {}
        },
        "fakultas-ilmu-sosial-dan-ilmu-politik": {
            "display_name": "Fakultas Ilmu Sosial dan Ilmu Politik",
            "majors": {}
        },
        "fakultas-kedokteran": {
            "display_name": "Fakultas Kedokteran",
            "majors": {}
        },
        "fakultas-kehutanan": {
            "display_name": "Fakultas Kehutanan",
            "majors": {}
        },
        "fakultas-keperawatan": {
            "display_name": "Fakultas Keperawatan",
            "majors": {}
        },
        "fakultas-kesehatan-masyarakat": {
            "display_name": "Fakultas Kesehatan Masyarakat",
            "majors": {}
        },
        "fakultas-matematika-dan-ilmu-peng-alam": {
            "display_name": "Fakultas Matematika dan Ilmu Peng. Alam",
            "majors": {}
        },
        "fakultas-pendidikan-dokter-gigi": {
            "display_name": "Fakultas Pendidikan Dokter Gigi",
            "majors": {}
        },
        "fakultas-pertanian": {
            "display_name": "Fakultas Pertanian",
            "majors": {}
        },
        "fakultas-peternakan": {
            "display_name": "Fakultas Peternakan",
            "majors": {}
        },
        "fakultas-teknik": {
            "display_name": "Fakultas Teknik",
            "majors": {}
        },
        "fakultas-vokasi": {
            "display_name": "Fakultas Vokasi",
            "majors": {}
        },
        "program-pascasarjana": {
            "display_name": "Program Pascasarjana",
            "majors": {}
        }
    }
    
    # Save the comprehensive config
    config.save_config(output_path)
    
    console.print(f"[green]✅ Comprehensive configuration created: {output_path}[/green]")
    console.print("\n[yellow]⚠️  IMPORTANT NEXT STEPS:[/yellow]")
    console.print("1. [cyan]Set your API key:[/cyan] Create .env file with GOOGLE_API_KEY")
    console.print("2. [cyan]Customize classification categories:[/cyan] Edit the categories in config.yaml for your research domain")
    console.print("3. [cyan]Update faculty/major data:[/cyan] Run 'pdm run python main.py discover' to get latest data")


def update_config_with_discovery(config_path: str = "config.yaml") -> Config:
    """
    Update existing configuration file with discovered faculty/major data.
    
    Args:
        config_path: Path to the configuration file to update.
        
    Returns:
        Updated Config object.
    """
    # Load existing config
    config = load_config(config_path)
    
    console.print("[blue]🔍 Starting discovery to update configuration...[/blue]")
    
    # Perform discovery
    from src.scraping.discovery import UNHASRepositoryDiscovery
    discovery = UNHASRepositoryDiscovery(verbose=config.verbose_logging)
    
    # Get new faculty data
    discovered_faculties = discovery.discover_all_faculties()
    
    if discovered_faculties:
        # Update the config with discovered data
        config.faculties = discovered_faculties
        
        console.print(f"[green]✅ Configuration updated with {len(discovered_faculties)} faculties![/green]")
        
        # Show summary
        console.print("\n[dim]Discovered faculties:[/dim]")
        for faculty_key, faculty_data in discovered_faculties.items():
            major_count = len(faculty_data.get('majors', {}))
            console.print(f"  • {faculty_data['display_name']} ({major_count} majors)")
            
    else:
        console.print("[red]❌ No faculties discovered[/red]")
        
    return config


def validate_and_prompt_categories(config: Config) -> Config:
    """
    Enhanced validation that prompts user to customize categories if needed.
    
    Args:
        config: Configuration object to validate and potentially modify.
        
    Returns:
        Config: Updated configuration object.
    """
    # Check if using default categories and prompt for customization
    if not config.user_defined_categories:
        # Check if categories are still default
        default_categories = {
            "Teori": "Penelitian yang fokus pada pengembangan teori dan konsep fundamental.",
            "Aplikasi": "Penelitian yang fokus pada penerapan teori untuk memecahkan masalah praktis.",
            "Eksperimental": "Penelitian yang melibatkan eksperimen dan pengujian empiris.",
            "Komputasi": "Penelitian yang menggunakan metode komputasi dan simulasi.",
            "Analisis Data": "Penelitian yang fokus pada analisis dan interpretasi data.",
            "Lainnya": "Kategori untuk penelitian yang tidak termasuk dalam kategori lain."
        }
        
        current_default = config.classification_categories.get("default", {})
        
        if current_default == default_categories:
            console.print("\n[yellow]⚠️  CLASSIFICATION CATEGORIES REVIEW NEEDED[/yellow]")
            console.print("[dim]You are currently using generic default categories:[/dim]")
            
            for i, (category, description) in enumerate(current_default.items(), 1):
                console.print(f"  {i}. [cyan]{category}[/cyan]: {description}")
            
            console.print("\n[red]For better classification accuracy, you should customize these![/red]")
            console.print("[dim]Recommendations:[/dim]")
            console.print("  • Use domain-specific terminology (e.g., 'Machine Learning', 'Regresi')")
            console.print("  • Make category distinctions clear and non-overlapping")
            console.print("  • Consider your research field's standard classifications")
            console.print("  • Include relevant statistical/mathematical methods")
            
            console.print("\n[cyan]💡 Example for Statistics major:[/cyan]")
            console.print("  • Regresi: Statistical modeling with predefined functions")
            console.print("  • Machine Learning: Prediction-focused algorithms") 
            console.print("  • Analisis Runtun Waktu: Time series analysis")
            console.print("  • Analisis Survival: Time-to-event analysis")
            
            from rich.prompt import Confirm
            
            customize = Confirm.ask("\n[bold]Do you want to customize categories now?[/bold]", default=True)
            
            if customize:
                console.print("\n[green]Great! Let's customize your classification categories![/green]")
                console.print("[dim]You'll need to edit the 'classification_categories' section in config.yaml[/dim]")
                
                if Confirm.ask("Open config file location?", default=True):
                    console.print(f"[cyan]Config file location: {os.path.abspath('config.yaml')}[/cyan]")
                    console.print("\n[yellow]📝 Please edit the config file now:[/yellow]")
                    console.print("1. Open config.yaml in your editor")
                    console.print("2. Find the 'classification_categories:' section")
                    console.print("3. Replace the default categories with your custom ones")
                    console.print("4. Set 'user_defined_categories: true'")
                    console.print("5. Save the file")
                
                # Wait for user to complete edits
                if Confirm.ask("\n[bold]Have you finished editing the config file?[/bold]", default=False):
                    console.print("\n[blue]🔄 Reloading configuration to check your changes...[/blue]")
                    
                    try:
                        # Reload the config to get the updated categories
                        updated_config = load_config("config.yaml", validate=False)
                        
                        # Check if categories were actually changed
                        updated_default = updated_config.classification_categories.get("default", {})
                        
                        if updated_default != default_categories:
                            console.print("[green]✅ Custom categories detected! Great work![/green]")
                            console.print(f"[dim]Found {len(updated_default)} custom categories[/dim]")
                            
                            # Show the new categories
                            console.print("\n[cyan]Your custom categories:[/cyan]")
                            for i, (category, description) in enumerate(updated_default.items(), 1):
                                console.print(f"  {i}. [green]{category}[/green]: {description}")
                            
                            # Check if user_defined_categories flag was set
                            if updated_config.user_defined_categories:
                                console.print("[green]✅ user_defined_categories flag is set correctly[/green]")
                                return updated_config
                            else:
                                console.print("[yellow]⚠️  Don't forget to set 'user_defined_categories: true' in config.yaml[/yellow]")
                                if Confirm.ask("Set it automatically?", default=True):
                                    updated_config.user_defined_categories = True
                                    updated_config.save_config()
                                    console.print("[green]✅ Flag set automatically![/green]")
                                return updated_config
                        else:
                            console.print("[yellow]⚠️  No changes detected in categories.[/yellow]")
                            console.print("[dim]Categories are still the same as defaults.[/dim]")
                            
                            retry = Confirm.ask("Try editing again?", default=True)
                            if retry:
                                console.print("[cyan]Please edit the config file and try again.[/cyan]")
                                return config  # Return original config, validation will be repeated
                            else:
                                console.print("[yellow]Continuing with default categories.[/yellow]")
                                return config
                    
                    except Exception as e:
                        console.print(f"[red]❌ Error reloading config: {e}[/red]")
                        console.print("[yellow]Continuing with current configuration.[/yellow]")
                        return config
                else:
                    console.print("\n[yellow]No problem! You can edit the categories later.[/yellow]")
                    console.print("[dim]Re-run validation after editing to check your changes.[/dim]")
                    return config
            else:
                console.print("\n[yellow]⚠️  Continuing with default categories.[/yellow]")
                console.print("[dim]You can customize them later by editing config.yaml[/dim]")
                
                # Ask if they want to mark as user-defined to skip future prompts
                skip_future = Confirm.ask("Skip this prompt in future runs?", default=False)
                if skip_future:
                    config.user_defined_categories = True
                    config.save_config()
                    console.print("[green]✅ Default categories accepted. Won't prompt again.[/green]")
                
                return config
        else:
            # Categories have been customized but flag not set
            console.print("[green]✅ Custom categories detected![/green]")
            return config
    else:
        # user_defined_categories is True, skip prompts
        return config


def resolve_faculty_key(faculties: dict, faculty_input: str) -> str:
    """
    Resolve faculty input (display name or key) to the actual faculty key.
    
    Args:
        faculties: Dictionary of faculty data from config
        faculty_input: Faculty name (can be display name or technical key)
        
    Returns:
        Faculty key if found, None otherwise
    """
    if not faculties or not faculty_input:
        return None
        
    # Try exact key match first
    if faculty_input in faculties:
        return faculty_input
    
    # Try to find by display name or partial match
    for faculty_key, faculty_data in faculties.items():
        if isinstance(faculty_data, dict) and 'display_name' in faculty_data:
            faculty_display = faculty_data['display_name']
        else:
            faculty_display = faculty_key.replace('-', ' ').title()
            
        if (faculty_input.lower() == faculty_key.lower() or 
            faculty_input.lower() == faculty_display.lower() or
            faculty_key.lower().replace(" ", "").replace(".", "") == faculty_input.lower().replace(" ", "").replace(".", "")):
            return faculty_key
    
    return None


def resolve_major_key(faculty_majors: dict, major_input: str) -> str:
    """
    Resolve major input (display name or key) to the actual major key.
    
    Args:
        faculty_majors: Dictionary of major data for a faculty
        major_input: Major name (can be display name or technical key)
        
    Returns:
        Major key if found, None otherwise
    """
    if not faculty_majors or not major_input:
        return None
        
    # Try exact key match first
    if major_input in faculty_majors:
        return major_input
    
    # Try to find by display name or partial match
    for major_key, major_data in faculty_majors.items():
        if isinstance(major_data, dict) and 'display_name' in major_data:
            major_display = major_data['display_name']
        else:
            major_display = major_key.replace('-', ' ').title()
            
        if (major_input.lower() == major_key.lower() or 
            major_input.lower() == major_display.lower() or
            major_key.lower().replace(" ", "").replace(".", "") == major_input.lower().replace(" ", "").replace(".", "")):
            return major_key
    
    return None


def validate_scraping_config(config: Config) -> None:
    """
    Validate configuration specifically for scraping operations that require target_faculty and target_major.
    
    Args:
        config: Configuration object to validate.
        
    Raises:
        ValueError: If required scraping configuration is missing.
    """
    if not config.target_faculty or not config.target_major:
        raise ValueError(
            "Target faculty and major must be specified for scraping operations.\n"
            "Please either:\n"
            "1. Run in interactive mode: python main.py --interactive\n"
            "2. Set target_faculty and target_major in config.yaml\n"
            "3. Use command line args: --faculty 'Faculty Name' --major 'Major Name'"
        )
    
    # Run normal validation for the targets
    validate_config(config)
    
    return config


