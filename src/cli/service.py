"""
Refactored CLI interface with improved separation of concerns.

This module provides a clean, maintainable CLI interface using
proper abstraction and dependency injection.
"""

from typing import Tuple, Optional, Dict, Any
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel

from ..core.abstractions import IUserInterface
from ..config.service import ApplicationConfig
from ..discovery.service import get_faculty_display_name, get_major_display_name


class RichUserInterface(IUserInterface):
    """Rich-based user interface implementation."""
    
    def __init__(self):
        self.console = Console()
    
    def display_welcome(self) -> None:
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
        self.console.print(Panel(welcome_text, expand=False, border_style="blue"))
    
    def select_faculty_major(self, faculties: Dict[str, Any]) -> Tuple[str, str]:
        """
        Interactive faculty/major selection with simple numbered lists.
        
        Args:
            faculties: Dictionary of available faculties
            
        Returns:
            Tuple of (faculty_key, major_key)
        """
        self.console.print("\n[bold blue]Faculty and Major Selection[/bold blue]")
        
        # Step 1: Select Faculty
        faculty_key = self._select_faculty(faculties)
        if not faculty_key:
            return None, None
        
        # Step 2: Select Major
        major_key = self._select_major(faculties, faculty_key)
        if not major_key:
            return None, None
        
        return faculty_key, major_key
    
    def display_progress(self, operation: str, progress: float) -> None:
        """
        Display operation progress.
        
        Args:
            operation: Operation name
            progress: Progress percentage (0.0 to 1.0)
        """
        percentage = int(progress * 100)
        bar_length = 20
        filled_length = int(bar_length * progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        self.console.print(f"\r[cyan]{operation}:[/cyan] [{bar}] {percentage}%", end="")
    
    def display_error(self, message: str) -> None:
        """
        Display error message.
        
        Args:
            message: Error message to display
        """
        self.console.print(f"[red]❌ Error: {message}[/red]")
    
    def display_success(self, message: str) -> None:
        """
        Display success message.
        
        Args:
            message: Success message to display
        """
        self.console.print(f"[green]✅ {message}[/green]")
    
    def display_warning(self, message: str) -> None:
        """
        Display warning message.
        
        Args:
            message: Warning message to display
        """
        self.console.print(f"[yellow]⚠️  {message}[/yellow]")
    
    def display_info(self, message: str) -> None:
        """
        Display info message.
        
        Args:
            message: Info message to display
        """
        self.console.print(f"[cyan]ℹ️  {message}[/cyan]")
    
    def _select_faculty(self, faculties: Dict[str, Any]) -> Optional[str]:
        """Select faculty from numbered list."""
        self.console.print("\n[bold]Step 1: Select Faculty[/bold]")
        faculty_list = list(faculties.keys())
        
        for i, faculty_key in enumerate(faculty_list, 1):
            faculty_display = get_faculty_display_name(faculties, faculty_key)
            self.console.print(f"  {i}. {faculty_display}")
        
        while True:
            try:
                choice = Prompt.ask(f"\nSelect faculty (1-{len(faculty_list)})", default="1")
                faculty_idx = int(choice) - 1
                if 0 <= faculty_idx < len(faculty_list):
                    selected_faculty = faculty_list[faculty_idx]
                    faculty_display = get_faculty_display_name(faculties, selected_faculty)
                    self.console.print(f"\n[green]✓ Selected: {faculty_display}[/green]")
                    return selected_faculty
                else:
                    self.console.print(f"[red]Please select a number between 1 and {len(faculty_list)}[/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number.[/red]")
        
        return None
    
    def _select_major(self, faculties: Dict[str, Any], faculty_key: str) -> Optional[str]:
        """Select major from numbered list."""
        faculty_data = faculties[faculty_key]
        faculty_display = get_faculty_display_name(faculties, faculty_key)
        
        # Handle nested structure vs old flat structure
        if isinstance(faculty_data, dict) and 'majors' in faculty_data:
            majors = faculty_data['majors']
            
            # Check if majors need to be discovered
            if not majors or len(majors) == 0:
                self.console.print(f"\n[yellow]Step 2: Discovering majors for {faculty_display}...[/yellow]")
                # This would need to be handled by the calling code
                self.display_error("Majors need to be discovered first")
                return None
        else:
            # Old flat structure
            majors = faculty_data
        
        self.console.print(f"\n[bold]Step 2: Select Major in {faculty_display}[/bold]")
        major_list = list(majors.keys())
        
        for i, major_key in enumerate(major_list, 1):
            if isinstance(majors[major_key], dict) and 'display_name' in majors[major_key]:
                major_display = majors[major_key]['display_name']
            else:
                major_display = get_major_display_name(major_key)
            self.console.print(f"  {i}. {major_display}")
        
        while True:
            try:
                choice = Prompt.ask(f"\nSelect major (1-{len(major_list)})", default="1")
                major_idx = int(choice) - 1
                if 0 <= major_idx < len(major_list):
                    selected_major = major_list[major_idx]
                    
                    # Get major display name for confirmation
                    if isinstance(majors[selected_major], dict) and 'display_name' in majors[selected_major]:
                        major_display = majors[selected_major]['display_name']
                    else:
                        major_display = get_major_display_name(selected_major)
                    
                    self.console.print(f"[green]✓ Selected: {major_display}[/green]")
                    return selected_major
                else:
                    self.console.print(f"[red]Please select a number between 1 and {len(major_list)}[/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number.[/red]")
        
        return None


class InteractiveFlowOrchestrator:
    """Orchestrator for interactive user flows."""
    
    def __init__(self, ui: IUserInterface, config: ApplicationConfig):
        """
        Initialize interactive flow orchestrator.
        
        Args:
            ui: User interface implementation
            config: Application configuration
        """
        self.ui = ui
        self.config = config
    
    def run_interactive_mode(self) -> Dict[str, Any]:
        """
        Run the application in interactive mode.
        
        Returns:
            Dictionary with user selections and operation choice
        """
        self.ui.display_welcome()
        
        # Check if user wants dynamic discovery
        if self._offer_dynamic_discovery():
            self._perform_dynamic_discovery()
        
        # Select operation
        operation = self._display_operation_menu()
        
        # Select faculty and major for scraping operations
        faculty_key = None
        major_key = None
        
        if operation in ["scrape", "all"]:
            faculty_key, major_key = self.ui.select_faculty_major(self.config.faculties)
            
            if not faculty_key or not major_key:
                self.ui.display_error("Faculty/major selection cancelled")
                return {"cancelled": True}
            
            # Update config with selections
            self.config.scraping.target_faculty = faculty_key
            self.config.scraping.target_major = major_key
            
            # Confirm settings
            if not self._confirm_settings(faculty_key, major_key):
                self.ui.display_warning("Operation cancelled")
                return {"cancelled": True}
        
        # Get input file for processing operations
        input_file = None
        if operation in ["classify", "export_excel", "simplify"]:
            input_file = self._get_input_file_interactive()
            if not input_file:
                self.ui.display_error("No input file selected. Operation cancelled.")
                return {"cancelled": True}
        
        return {
            "operation": operation,
            "faculty_key": faculty_key,
            "major_key": major_key,
            "input_file": input_file,
            "cancelled": False
        }
    
    def _offer_dynamic_discovery(self) -> bool:
        """Ask user if they want to perform dynamic discovery."""
        if not self.config.enable_dynamic_discovery:
            return False
        
        if not self.config.faculties:
            self.ui.display_info("No faculty data found in configuration")
            return Confirm.ask("🔍 Would you like to discover available faculties and majors?", default=True)
        
        return Confirm.ask("🔄 Would you like to update faculty/major data from the repository?", default=False)
    
    def _perform_dynamic_discovery(self) -> None:
        """Perform dynamic discovery of faculties and majors."""
        try:
            from ..discovery.service import UNHASDiscoveryService
            from ..config.service import ConfigurationService
            
            self.ui.display_info("Starting dynamic discovery...")
            discovery_service = UNHASDiscoveryService(
                headless=self.config.scraping.headless_browser,
                verbose=self.config.verbose_logging
            )
            
            updated_config = discovery_service.update_config_with_discovered_data(self.config)
            self.config.faculties = updated_config.faculties
            
            # Save the updated configuration to file
            config_service = ConfigurationService()
            config_service.save_config(self.config, "config.yaml")
            
            self.ui.display_success("Discovery completed successfully")
            self.ui.display_info("Configuration updated: config.yaml")
            
        except Exception as e:
            self.ui.display_error(f"Discovery failed: {e}")
    
    def _display_operation_menu(self) -> str:
        """Display operation selection menu."""
        self.ui.console.print("\n[bold blue]Operation Selection[/bold blue]")
        
        operations = [
            ("scrape", "Scrape thesis data from repository"),
            ("classify", "Classify existing thesis data"),
            ("export_excel", "Export data to Excel format"),
            ("simplify", "Create simplified JSON data"),
            ("all", "Run complete pipeline (scrape + classify + export)")
        ]
        
        for i, (op, desc) in enumerate(operations, 1):
            self.ui.console.print(f"  {i}. {desc}")
        
        while True:
            try:
                choice = Prompt.ask(f"\nSelect operation (1-{len(operations)})", default="5")
                op_idx = int(choice) - 1
                if 0 <= op_idx < len(operations):
                    selected_operation = operations[op_idx][0]
                    self.ui.console.print(f"\n[green]✓ Selected: {operations[op_idx][1]}[/green]")
                    return selected_operation
                else:
                    self.ui.display_error(f"Please select a number between 1 and {len(operations)}")
            except ValueError:
                self.ui.display_error("Please enter a valid number")
        
        return "all"  # Fallback
    
    def _confirm_settings(self, faculty_key: str, major_key: str) -> bool:
        """Confirm user settings before proceeding."""
        faculty_display = get_faculty_display_name(self.config.faculties, faculty_key)
        major_display = get_major_display_name(major_key, self.config.faculties[faculty_key].get('majors', {}).get(major_key))
        
        self.ui.console.print("\n[bold cyan]🔍 Configuration Summary[/bold cyan]")
        self.ui.console.print(f"Faculty: [green]{faculty_display}[/green]")
        self.ui.console.print(f"Major: [green]{major_display}[/green]")
        self.ui.console.print(f"Output Directory: [blue]{self.config.processing.output_dir}[/blue]")
        
        return Confirm.ask("\n[bold]Do you want to proceed with these settings?[/bold]", default=True)
    
    def _get_input_file_interactive(self) -> Optional[str]:
        """Get input file through interactive selection."""
        import os
        
        output_dir = self.config.processing.output_dir
        
        if not os.path.exists(output_dir):
            self.ui.display_error(f"Output directory '{output_dir}' does not exist")
            return None
        
        # Find JSON files in output directory
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        
        if not json_files:
            self.ui.display_error(f"No JSON files found in '{output_dir}'")
            return None
        
        self.ui.console.print("\n[bold]Available input files:[/bold]")
        for i, filename in enumerate(json_files, 1):
            self.ui.console.print(f"  {i}. {filename}")
        
        while True:
            try:
                choice = Prompt.ask(f"\nSelect input file (1-{len(json_files)})", default="1")
                file_idx = int(choice) - 1
                if 0 <= file_idx < len(json_files):
                    selected_file = os.path.join(output_dir, json_files[file_idx])
                    self.ui.console.print(f"\n[green]✓ Selected: {json_files[file_idx]}[/green]")
                    return selected_file
                else:
                    self.ui.display_error(f"Please select a number between 1 and {len(json_files)}")
            except ValueError:
                self.ui.display_error("Please enter a valid number")
        
        return None
