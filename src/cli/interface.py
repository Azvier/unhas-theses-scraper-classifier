"""
Interactive CLI interface for UNHAS Theses Scraper.
"""

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from typing import Tuple, Optional

from ..config.settings import Config
from ..scraping.discovery import UNHASRepositoryDiscovery, get_faculty_display_name, get_major_display_name

console = Console()


def display_welcome():
    """Display welcome message and project info."""
    welcome_text = """
[bold blue]UNHAS Theses Scraper[/bold blue]

A tool to scrape, classify, and process thesis data from 
the Hasanuddin University repository.

Features:
• Multi-faculty and multi-major support
• AI-powered classification with primary/secondary focus
• Multiple output formats (JSON, Excel)
• Configurable settings
    """
    console.print(Panel(welcome_text, expand=False, border_style="blue"))


def display_faculties_and_majors(config: Config):
    """Display available faculties and majors in a simple list format."""
    console.print("\n[bold cyan]Available Faculties:[/bold cyan]")
    
    for i, (faculty_key, faculty_data) in enumerate(config.faculties.items(), 1):
        faculty_display = get_faculty_display_name(config.faculties, faculty_key)
        
        # Handle new nested structure
        if isinstance(faculty_data, dict) and 'majors' in faculty_data:
            majors = faculty_data['majors']
            if majors and len(majors) > 0:
                # Majors have been discovered
                console.print(f"  {i}. [green]{faculty_display}[/green] ({len(majors)} majors available)")
            else:
                # Majors haven't been discovered yet
                console.print(f"  {i}. [green]{faculty_display}[/green]")
        else:
            # Handle old flat structure (fallback)
            major_count = len(faculty_data.keys())
            console.print(f"  {i}. [green]{faculty_display}[/green] ({major_count} majors available)")
    
    console.print()


def select_faculty_major_interactive(config: Config) -> Tuple[str, str]:
    """Interactive selection of faculty and major with simple numbered lists."""
    console.print("\n[bold blue]Faculty and Major Selection[/bold blue]")
    
    # Step 1: Select Faculty from numbered list
    console.print("\n[bold]Step 1: Select Faculty[/bold]")
    faculty_list = list(config.faculties.keys())
    
    for i, faculty_key in enumerate(faculty_list, 1):
        faculty_display = get_faculty_display_name(config.faculties, faculty_key)
        console.print(f"  {i}. {faculty_display}")
    
    while True:
        try:
            choice = Prompt.ask(f"\nSelect faculty (1-{len(faculty_list)})", default="1")
            faculty_idx = int(choice) - 1
            if 0 <= faculty_idx < len(faculty_list):
                selected_faculty = faculty_list[faculty_idx]
                break
            else:
                console.print(f"[red]Please select a number between 1 and {len(faculty_list)}[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")
    
    faculty_display = get_faculty_display_name(config.faculties, selected_faculty)
    console.print(f"\n[green]✓ Selected: {faculty_display}[/green]")
    
    # Step 2: Discover majors for selected faculty if needed
    faculty_data = config.faculties[selected_faculty]
    if isinstance(faculty_data, dict) and 'majors' in faculty_data:
        majors = faculty_data['majors']
        if not majors or len(majors) == 0:
            console.print(f"\n[yellow]Step 2: Discovering majors for {faculty_display}...[/yellow]")
            from src.scraping.discovery import UNHASRepositoryDiscovery
            
            discovery = UNHASRepositoryDiscovery(verbose=config.verbose_logging)
            updated_config = discovery.discover_majors_for_faculty_on_demand(config, selected_faculty)
            
            if updated_config and hasattr(updated_config, 'faculties'):
                config.faculties[selected_faculty]['majors'] = updated_config.faculties[selected_faculty]['majors']
                config.save_config()
                major_count = len(updated_config.faculties[selected_faculty]['majors'])
                console.print(f"[green]✓ Found {major_count} majors[/green]")
            else:
                console.print("[red]✗ Failed to discover majors[/red]")
                return None, None
    
    # Step 3: Select Major from numbered list
    console.print(f"\n[bold]Step 3: Select Major in {faculty_display}[/bold]")
    faculty_data = config.faculties[selected_faculty]
    
    if isinstance(faculty_data, dict) and 'majors' in faculty_data:
        majors = faculty_data['majors']
        major_list = list(majors.keys())
        
        for i, major_key in enumerate(major_list, 1):
            if isinstance(majors[major_key], dict) and 'display_name' in majors[major_key]:
                major_display = majors[major_key]['display_name']
            else:
                major_display = get_major_display_name(major_key)
            console.print(f"  {i}. {major_display}")
    else:
        major_list = list(faculty_data.keys())
        for i, major_key in enumerate(major_list, 1):
            major_display = get_major_display_name(major_key)
            console.print(f"  {i}. {major_display}")
    
    while True:
        try:
            choice = Prompt.ask(f"\nSelect major (1-{len(major_list)})", default="1")
            major_idx = int(choice) - 1
            if 0 <= major_idx < len(major_list):
                selected_major = major_list[major_idx]
                break
            else:
                console.print(f"[red]Please select a number between 1 and {len(major_list)}[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")
    
    # Get major display name for confirmation
    if isinstance(faculty_data, dict) and 'majors' in faculty_data:
        majors = faculty_data['majors']
        if isinstance(majors[selected_major], dict) and 'display_name' in majors[selected_major]:
            major_display = majors[selected_major]['display_name']
        else:
            major_display = get_major_display_name(selected_major)
    else:
        major_display = get_major_display_name(selected_major)
    
    console.print(f"[green]✓ Selected: {major_display}[/green]")
    
    return selected_faculty, selected_major


def confirm_settings(config: Config, faculty: str, major: str) -> bool:
    """Display current settings and confirm with user."""
    faculty_display = get_faculty_display_name(config.faculties, faculty)
    major_display = get_major_display_name(major)
    
    # Get the target URL
    faculty_data = config.faculties[faculty]
    if isinstance(faculty_data, dict) and 'majors' in faculty_data:
        # New nested structure
        major_data = faculty_data['majors'][major]
        if isinstance(major_data, dict) and 'url' in major_data:
            target_url = major_data['url']
        else:
            target_url = major_data
    else:
        # Old flat structure
        target_url = faculty_data[major]
    
    settings_info = f"""
[bold]Current Settings:[/bold]

Faculty: [cyan]{faculty_display}[/cyan]
Major: [green]{major_display}[/green]
Output Directory: [yellow]{config.output_dir}[/yellow]
Batch Size: [yellow]{config.batch_size}[/yellow]
Headless Browser: [yellow]{config.headless_browser}[/yellow]

Target URL: [blue]{target_url}[/blue]
    """
    
    console.print(Panel(settings_info, title="Configuration", border_style="yellow"))
    
    return Confirm.ask("Proceed with these settings?", default=True)


def display_operation_menu() -> str:
    """Display operation selection menu."""
    operations = [
        ("scrape", "Scrape thesis data only"),
        ("classify", "Classify existing data only"), 
        ("export", "Export existing data to Excel"),
        ("simplify", "Create simplified JSON from existing data"),
        ("all", "Run full pipeline (scrape + classify + export)"),
    ]
    
    console.print("\n[bold]Select Operation:[/bold]")
    for i, (op, desc) in enumerate(operations, 1):
        console.print(f"  {i}. [cyan]{op}[/cyan] - {desc}")
    
    while True:
        try:
            choice = int(Prompt.ask(
                f"Enter your choice (1-{len(operations)})",
                default="5"  # Default to "all"
            ))
            if 1 <= choice <= len(operations):
                selected_op = operations[choice - 1][0]
                console.print(f"Selected operation: [cyan]{selected_op}[/cyan]")
                return selected_op
            else:
                console.print("[red]Invalid choice. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")


def get_input_file_interactive(output_dir: str) -> Optional[str]:
    """Interactive input file selection for classification/export operations."""
    import os
    import glob
    
    # Look for JSON files in output directory
    json_files = glob.glob(os.path.join(output_dir, "*.json"))
    
    if not json_files:
        console.print(f"[red]No JSON files found in {output_dir}[/red]")
        return None
    
    # Sort by modification time (newest first)
    json_files.sort(key=os.path.getmtime, reverse=True)
    
    console.print("\n[bold]Available input files:[/bold]")
    for i, file_path in enumerate(json_files[:10], 1):  # Show max 10 files
        filename = os.path.basename(file_path)
        mod_time = os.path.getmtime(file_path)
        from datetime import datetime
        time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
        console.print(f"  {i}. {filename} (modified: {time_str})")
    
    if len(json_files) > 10:
        console.print(f"  ... and {len(json_files) - 10} more files")
    
    while True:
        try:
            choice = int(Prompt.ask(
                f"Select file (1-{min(10, len(json_files))})",
                default="1"
            ))
            if 1 <= choice <= min(10, len(json_files)):
                selected_file = json_files[choice - 1]
                console.print(f"Selected file: [yellow]{os.path.basename(selected_file)}[/yellow]")
                return selected_file
            else:
                console.print("[red]Invalid choice. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")


def display_progress_start(operation: str, details: str = ""):
    """Display operation start message."""
    message = f"Starting {operation}..."
    if details:
        message += f" ({details})"
    
    console.print(f"\n[bold green]🚀 {message}[/bold green]")


def display_progress_complete(operation: str, output_file: str = ""):
    """Display operation completion message."""
    message = f"✅ {operation} completed!"
    if output_file:
        message += f"\nOutput: [yellow]{output_file}[/yellow]"
    
    console.print(f"\n[bold green]{message}[/bold green]")


def offer_dynamic_discovery(config: Config) -> bool:
    """Ask user if they want to discover faculties/majors dynamically."""
    # Note: enable_dynamic_discovery should not force discovery in interactive mode
    # It's mainly for non-interactive automated workflows
    
    # Check if faculties already exist in config
    has_faculties = hasattr(config, 'faculties') and config.faculties
    
    if has_faculties:
        # Count existing faculties and majors
        total_faculties = len(config.faculties)
        total_majors = sum(
            len(faculty_data.get('majors', {})) 
            for faculty_data in config.faculties.values() 
            if isinstance(faculty_data, dict)
        )
        
        # Check if this looks like real discovered data (many majors) or just default placeholders
        avg_majors_per_faculty = total_majors / total_faculties if total_faculties > 0 else 0
        is_populated_data = avg_majors_per_faculty > 3  # Heuristic: >3 majors per faculty on average indicates discovered data
        
        if is_populated_data:
            # This looks like real discovered data
            console.print("\n[cyan]📊 Current configuration data:[/cyan]")
            console.print(f"  • [green]{total_faculties} faculties[/green]")
            console.print(f"  • [green]{total_majors} majors[/green]")
            console.print("\n[dim]Your configuration already contains comprehensive faculty and major data.[/dim]")
            console.print("[yellow]You can discover faculties and majors dynamically from the UNHAS website.[/yellow]")
            console.print("[yellow]This may take a few minutes but will refresh your data with the latest options.[/yellow]")
            
            return Confirm.ask("Would you like to refresh faculty data by running discovery?", default=False)
        else:
            # This looks like default/placeholder data with mostly empty majors
            console.print("\n[cyan]📊 Current configuration status:[/cyan]")
            console.print(f"  • [yellow]{total_faculties} faculties (mostly empty)[/yellow]")
            console.print(f"  • [yellow]{total_majors} majors (limited data)[/yellow]")
            console.print("\n[dim]Your configuration contains basic faculty structure but lacks comprehensive major data.[/dim]")
            console.print("[yellow]You can discover all faculties and majors dynamically from the UNHAS website.[/yellow]")
            console.print("[yellow]This may take a few minutes but will populate your configuration with complete data.[/yellow]")
            
            return Confirm.ask("Would you like to discover comprehensive faculty/major data from UNHAS website?", default=True)
    else:
        console.print("\n[yellow]⚠️  No faculty data found in your configuration.[/yellow]")
        console.print("[yellow]You can discover faculties and majors dynamically from the UNHAS website.[/yellow]")
        console.print("[yellow]This may take a few minutes but will give you the most up-to-date options.[/yellow]")
        
        return Confirm.ask("Would you like to discover faculties and majors from UNHAS website?", default=True)


def perform_dynamic_discovery(config: Config) -> Config:
    """Perform dynamic discovery and update configuration."""
    console.print("\n[blue]🔍 Starting dynamic discovery...[/blue]")
    
    discovery = UNHASRepositoryDiscovery(headless=config.headless_browser, verbose=config.verbose_logging)
    
    try:
        updated_config = discovery.update_config_with_discovered_data(config)
        console.print("[green]✅ Dynamic discovery completed![/green]")
        return updated_config
    except Exception as e:
        console.print(f"[red]❌ Dynamic discovery failed: {e}[/red]")
        console.print("[yellow]Continuing with default configuration...[/yellow]")
        return config


def display_error(message: str):
    """Display error message."""
    console.print(f"\n[bold red]❌ Error: {message}[/bold red]")
