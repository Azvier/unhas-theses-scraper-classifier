"""
UNHAS Theses Scraper - Main CLI Application

Enhanced version with configuration support, multi-major functionality,
secondary study focus, and improved user interface.
"""

import argparse
import os
import sys
from pathlib import Path

from rich.console import Console

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Config, load_config, validate_config, create_default_config_file, update_config_with_discovery, validate_scraping_config
from src.classification.classifier import classify_theses
from src.processing.data_processor import convert_json_to_excel, simplify_repository_data
from src.scraping.scraper import scrape_repository
from src.cli.interface import (
    display_welcome, display_faculties_and_majors, select_faculty_major_interactive,
    confirm_settings, display_operation_menu, get_input_file_interactive,
    display_progress_start, display_progress_complete, display_error,
    offer_dynamic_discovery, perform_dynamic_discovery, get_faculty_display_name
)

console = Console()


def create_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="UNHAS Theses Scraper and Classifier - Enhanced Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with default settings
  python main.py all

  # Interactive mode (recommended for first-time users)
  python main.py --interactive

  # Scrape specific faculty/major using display names (user-friendly)
  python main.py scrape --faculty "Fakultas Teknik" --major "Teknik Elektro"
  
  # Or using technical keys (both formats work)
  python main.py scrape --faculty fakultas-teknik --major teknik-elektro

  # Classify existing data with custom config
  python main.py classify --config my_config.yaml --input output/data.json

  # List all available faculties
  python main.py list-faculties

  # List majors for a specific faculty (display name or key works)
  python main.py list-majors --faculty "Fakultas Matematika dan Ilmu Peng. Alam"
  python main.py list-majors --faculty fakultas-matematika-dan-ilmu-peng-alam

  # Export to Excel format
  python main.py export_excel --input_file output/data.json

  # Create simplified JSON
  python main.py simplify --input_file output/data.json

  # Create default config file
  python main.py create-config
  
  # Validate current configuration
  python main.py validate-config
  
  # Discover all available faculties and majors from UNHAS website
  python main.py discover

Note: Faculty and major names can be specified using either:
  - Display names: "Fakultas Teknik", "Teknik Elektro" (user-friendly)
  - Technical keys: "fakultas-teknik", "teknik-elektro" (backward compatible)
        """
    )
    
    # Main command
    parser.add_argument(
        "command",
        nargs="?",
        choices=["scrape", "classify", "simplify", "export_excel", "all", 
                "list-majors", "list-faculties", "create-config", "validate-config",
                "discover", "update-config"],
        default="all",
        help="The command to execute (default: all)"
    )
    
    # Configuration options
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file (YAML format)"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    # Faculty/Major selection
    parser.add_argument(
        "--faculty", "-f",
        type=str,
        help='Target faculty (display name like "Fakultas Teknik" or key like "fakultas-teknik")'
    )
    
    parser.add_argument(
        "--major", "-m",
        type=str,
        help='Target major (display name like "Teknik Elektro" or key like "teknik-elektro")'
    )
    
    # Input/Output options
    parser.add_argument(
        "--input_file",
        type=str,
        help="Path to input JSON file for classification, simplification, or export"
    )
    
    parser.add_argument(
        "--output_dir",
        type=str,
        help="Directory to save output files (overrides config)"
    )
    
    # Processing options
    parser.add_argument(
        "--batch_size",
        type=int,
        help="Batch size for classification (overrides config)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in non-headless mode (visible)"
    )
    
    parser.add_argument(
        "--force-classify",
        action="store_true",
        help="Force classification even with default categories (for testing)"
    )
    
    return parser


def run_interactive_mode(config: Config):
    """Run the application in interactive mode."""
    display_welcome()
    
    # Check if user wants dynamic discovery
    if offer_dynamic_discovery(config):
        config = perform_dynamic_discovery(config)
    
    # Select operation
    operation = display_operation_menu()
    
    # Select faculty and major for scraping operations
    if operation in ["scrape", "all"]:
        faculty, major = select_faculty_major_interactive(config)
        
        # Update config with selections
        config.target_faculty = faculty
        config.target_major = major
        
        # Save the updated configuration to make it persistent
        config.save_config()
        console.print(f"[dim]💾 Saved selection to config: {faculty} -> {major}[/dim]")
        
        # Confirm settings
        if not confirm_settings(config, faculty, major):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
    
    # Get input file for processing operations
    input_file = None
    if operation in ["classify", "export_excel", "simplify"]:
        input_file = get_input_file_interactive(config.output_dir)
        if not input_file:
            console.print("[red]No input file selected. Operation cancelled.[/red]")
            return
    
    # Execute the selected operation
    execute_operation(operation, config, input_file=input_file)


def execute_operation(operation: str, config: Config, input_file: str = None, force_classify: bool = False):
    """Execute the specified operation."""
    try:
        if operation == "scrape":
            # Validate that we have the required faculty/major targets
            validate_scraping_config(config)
            display_progress_start("scraping", f"{config.target_faculty} - {config.target_major}")
            result = scrape_repository(
                output_dir=config.output_dir,
                config=config
            )
            if result:
                display_progress_complete("Scraping", result)
            return result
            
        elif operation == "classify":
            if not input_file:
                display_error("Input file required for classification")
                return None
            
            display_progress_start("classification")
            result = classify_theses(
                input_filename=input_file,
                output_dir=config.output_dir,
                config=config,
                force_default_categories=force_classify
            )
            if result:
                display_progress_complete("Classification", result)
            return result
            
        elif operation == "export_excel":
            if not input_file:
                display_error("Input file required for Excel export")
                return None
            
            display_progress_start("Excel export")
            result = convert_json_to_excel(
                input_path=input_file,
                output_dir=config.output_dir,
                config=config
            )
            if result:
                display_progress_complete("Excel export", result)
            return result
            
        elif operation == "simplify":
            if not input_file:
                display_error("Input file required for simplification")
                return None
            
            display_progress_start("data simplification")
            result = simplify_repository_data(
                input_path=input_file,
                output_dir=config.output_dir,
                config=config
            )
            if result:
                display_progress_complete("Data simplification", result)
            return result
            
        elif operation == "all":
            # Validate that we have the required faculty/major targets for scraping
            validate_scraping_config(config)
            display_progress_start("full pipeline", f"{config.target_faculty} - {config.target_major}")
            
            # 1. Scrape
            scraped_file = scrape_repository(
                output_dir=config.output_dir,
                config=config
            )
            if not scraped_file:
                display_error("Scraping failed. Aborting pipeline.")
                return None
            
            console.print(f"✅ Scraping completed: {scraped_file}")
            
            # 2. Classify
            classified_file = classify_theses(
                input_filename=scraped_file,
                output_dir=config.output_dir,
                config=config
            )
            if not classified_file:
                display_error("Classification failed. Aborting pipeline.")
                return None
            
            console.print(f"✅ Classification completed: {classified_file}")
            
            # 3. Post-processing
            results = []
            if config.enable_excel_export:
                excel_file = convert_json_to_excel(
                    input_path=classified_file,
                    output_dir=config.output_dir,
                    config=config
                )
                if excel_file:
                    results.append(excel_file)
            
            if config.enable_simplified_json:
                simplified_file = simplify_repository_data(
                    input_path=classified_file,
                    output_dir=config.output_dir,
                    config=config
                )
                if simplified_file:
                    results.append(simplified_file)
            
            display_progress_complete("Full pipeline", f"Generated {len(results) + 1} files")
            return classified_file
            
    except Exception as e:
        display_error(f"Operation failed: {str(e)}")
        return None


def list_faculties(config: Config):
    """List all available faculties."""
    console.print("\n[bold]Available Faculties:[/bold]")
    for faculty_key in config.faculties.keys():
        faculty_display = get_faculty_display_name(config.faculties, faculty_key)
        console.print(f"  • [cyan]{faculty_display}[/cyan]")


def list_majors(config: Config, faculty: str = None):
    """List majors for a specific faculty or all faculties."""
    if faculty:
        # Try to find faculty by exact key match first
        found_faculty = None
        if faculty in config.faculties:
            found_faculty = faculty
        else:
            # Try to find by display name or partial match
            for faculty_key, faculty_data in config.faculties.items():
                faculty_display = get_faculty_display_name(config.faculties, faculty_key)
                if (faculty.lower() == faculty_key.lower() or 
                    faculty.lower() == faculty_display.lower() or
                    faculty_key.lower().replace(" ", "").replace(".", "") == faculty.lower().replace(" ", "").replace(".", "")):
                    found_faculty = faculty_key
                    break
        
        if not found_faculty:
            display_error(f"Unknown faculty: {faculty}")
            console.print("\n[bold]Available faculties:[/bold]")
            for i, faculty_key in enumerate(config.faculties.keys(), 1):
                faculty_display = get_faculty_display_name(config.faculties, faculty_key)
                console.print(f"  {i}. {faculty_display} (key: {faculty_key})")
            return
        
        # Check if majors need to be discovered on-demand
        faculty_data = config.faculties[found_faculty]
        if isinstance(faculty_data, dict) and 'majors' in faculty_data:
            majors = faculty_data['majors']
            if not majors or len(majors) == 0:
                # Majors haven't been discovered yet, discover them now
                console.print(f"\n[yellow]Discovering majors for {get_faculty_display_name(config.faculties, found_faculty)}...[/yellow]")
                from src.scraping.discovery import UNHASRepositoryDiscovery
                
                discovery = UNHASRepositoryDiscovery(verbose=config.verbose_logging)
                updated_config = discovery.discover_majors_for_faculty_on_demand(config, found_faculty)
                
                if updated_config:
                    # Update the in-memory config with discovered majors
                    config = updated_config
                    # Save updated config to file
                    config.save_config()
                    majors = config.faculties[found_faculty]['majors']
                    console.print(f"[green]✓ Discovered {len(majors)} majors[/green]\n")
                else:
                    console.print("[red]✗ Failed to discover majors[/red]\n")
                    return
        
        console.print(f"\n[bold]Majors in {get_faculty_display_name(config.faculties, found_faculty)}:[/bold]")
        faculty_data = config.faculties[found_faculty]
        
        # Handle new nested structure
        if isinstance(faculty_data, dict) and 'majors' in faculty_data:
            majors = faculty_data['majors']
            for i, (major_key, major_data) in enumerate(majors.items(), 1):
                if isinstance(major_data, dict) and 'display_name' in major_data:
                    console.print(f"  {i}. {major_data['display_name']}")
                else:
                    console.print(f"  {i}. {major_key}")
        else:
            # Handle old flat structure
            for i, major in enumerate(faculty_data.keys(), 1):
                console.print(f"  {i}. {major}")
    else:
        display_faculties_and_majors(config)


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle special commands that don't require full config
    if args.command == "create-config":
        output_path = "config.yaml"
        create_default_config_file(output_path)
        return
    
    if args.command == "discover":
        # Perform dynamic discovery and update configuration
        try:
            from src.scraping.discovery import UNHASRepositoryDiscovery
            console.print("[blue]🔍 Starting dynamic discovery of UNHAS faculties and majors...[/blue]")
            console.print("[cyan]Using the new efficient discovery system that gets all data from the main page![/cyan]")
            
            # Determine config file path
            config_path = args.config if args.config else "config.yaml"
            
            # Load config to get settings, create if doesn't exist
            try:
                config = load_config(config_path)
                verbose = config.verbose_logging
            except Exception:
                console.print("[yellow]⚠️  Config file not found. Creating default configuration...[/yellow]")
                create_default_config_file(config_path)
                config = load_config(config_path)
                verbose = config.verbose_logging
            
            discovery = UNHASRepositoryDiscovery(headless=not args.no_headless, verbose=verbose)
            
            # Use the new efficient discovery method
            discovered_data = discovery.discover_faculties_and_majors_from_main_page()
            
            if discovered_data:
                total_faculties = len(discovered_data)
                total_majors = sum(len(majors) for majors in discovered_data.values())
                
                console.print(f"\n[green]✅ Discovery completed! Found {total_faculties} faculties with {total_majors} total majors:[/green]")
                
                # Check if config already has faculties (warn about merge)
                if hasattr(config, 'faculties') and config.faculties:
                    console.print("\n[yellow]ℹ️  Existing faculty configuration detected. Updating with discovered data...[/yellow]")
                    console.print("[dim]- Faculty and major data will be updated with latest from repository[/dim]")
                    console.print("[dim]- URLs will be updated to current values[/dim]")
                
                # Display discovered data
                for faculty_key, majors in discovered_data.items():
                    faculty_display = faculty_key.replace('-', ' ').title()
                    console.print(f"\n[cyan]{faculty_display}:[/cyan]")
                    for major_key in majors.keys():
                        major_display = major_key.replace('-', ' ').title()
                        console.print(f"  • {major_display}")
                
                # Update the configuration with discovered data (preserving existing user configurations)
                console.print(f"\n[blue]📝 Updating configuration file: {config_path}[/blue]")
                
                # Convert discovery format to config format and merge with existing config
                existing_faculties = config.faculties if hasattr(config, 'faculties') and config.faculties else {}
                
                # Initialize config_faculties OUTSIDE the loop to avoid resetting it
                config_faculties = existing_faculties.copy() if existing_faculties else {}
                
                for faculty_key, majors in discovered_data.items():
                    faculty_display = faculty_key.replace('-', ' ').title()
                    
                    # Preserve existing faculty configuration if it exists
                    if faculty_key in existing_faculties:
                        existing_faculty = existing_faculties[faculty_key]
                        # Keep existing display_name if user has customized it
                        if isinstance(existing_faculty, dict) and 'display_name' in existing_faculty:
                            faculty_display = existing_faculty['display_name']
                        
                        # Merge majors (preserve existing, add new ones)
                        existing_majors = existing_faculty.get('majors', {}) if isinstance(existing_faculty, dict) else {}
                    else:
                        existing_majors = {}
                    
                    # Create or update faculty entry
                    config_faculties[faculty_key] = {
                        "display_name": faculty_display,
                        "majors": existing_majors.copy()
                    }
                    
                    # Add new majors from discovery (preserve existing major configurations)
                    for major_key, major_info in majors.items():
                        # Extract URL from major_info dict
                        major_url = major_info['url'] if isinstance(major_info, dict) else major_info
                        
                        if major_key not in existing_majors:
                            # New major discovered
                            major_display = major_key.replace('-', ' ').title()
                            config_faculties[faculty_key]["majors"][major_key] = {
                                "display_name": major_display,
                                "url": major_url
                            }
                        else:
                            # Major exists, only update URL if it has changed
                            existing_major = existing_majors[major_key]
                            if isinstance(existing_major, dict):
                                existing_major["url"] = major_url  # Update URL in case it changed
                            else:
                                # Convert old format to new format
                                major_display = major_key.replace('-', ' ').title()
                                config_faculties[faculty_key]["majors"][major_key] = {
                                    "display_name": major_display,
                                    "url": major_url
                                }
                
                # Update config object with merged data
                config.faculties = config_faculties
                
                # Save updated configuration
                config.save_config(config_path)
                
                # Count new vs existing items for summary
                total_faculties = len(config_faculties)
                total_majors = sum(len(faculty_data.get('majors', {})) for faculty_data in config_faculties.values())
                
                console.print("[green]✅ Configuration updated with discovered faculty/major data![/green]")
                console.print(f"[cyan]Updated file: {config_path}[/cyan]")
                console.print(f"[dim]Total: {total_faculties} faculties, {total_majors} majors[/dim]")
                
            else:
                console.print("[red]❌ No faculties/majors discovered[/red]")
                
        except Exception as e:
            console.print(f"[red]❌ Discovery failed: {e}[/red]")
        return
    
    # Handle update-config command
    if args.command == "update-config":
        try:
            config_path = args.config if args.config else "config.yaml"
            config = load_config(config_path)
            updated_config = update_config_with_discovery(config)
            updated_config.save_config(config_path)
            console.print(f"[green]✓ Configuration updated: {config_path}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Configuration update failed: {e}[/red]")
        return
    
    # Load configuration
    try:
        # For create-config and discover commands, skip validation
        skip_validation = args.command in ["create-config", "discover", "update-config"]
        config_path = args.config if args.config else "config.yaml"
        
        # Special handling for commands that need a config file but it doesn't exist
        commands_needing_config = ["validate-config", "scrape", "classify", "all", "list-faculties", "list-majors"]
        if args.command in commands_needing_config and not os.path.exists(config_path):
            console.print(f"[yellow]⚠️  Config file not found: {config_path}[/yellow]")
            console.print("[blue]🔧 Creating default configuration file...[/blue]")
            create_default_config_file(config_path)
            console.print(f"[green]✅ Created default config: {config_path}[/green]")
            
            if args.command == "validate-config":
                console.print("\n[cyan]ℹ️  You may want to customize the configuration before proceeding.[/cyan]")
            else:
                console.print("\n[cyan]ℹ️  Default configuration created. You may want to run 'pdm run python main.py discover' to populate faculty data.[/cyan]")
        
        config = load_config(config_path, validate=not skip_validation)
        
        # Apply command line overrides
        if args.faculty:
            config.target_faculty = args.faculty
        if args.major:
            config.target_major = args.major
        if args.output_dir:
            config.output_dir = args.output_dir
        if args.batch_size:
            config.batch_size = args.batch_size
        if args.no_headless:
            config.headless_browser = False
        
        # Validate configuration
        if args.command == "validate-config":
            validate_config(config)
            console.print("[green]✅ Configuration is valid![/green]")
            return
        
        # NOTE: Classification validation is now handled within classify_theses function
        # This allows non-classification operations to proceed normally
        
    except Exception as e:
        display_error(f"Configuration error: {str(e)}")
        console.print("\n[yellow]Try running:[/yellow] python main.py create-config")
        return
    
    # Handle list commands
    if args.command == "list-faculties":
        list_faculties(config)
        return
    elif args.command == "list-majors":
        list_majors(config, args.faculty)
        return
    
    # Ensure output directory exists
    os.makedirs(config.output_dir, exist_ok=True)
    
    # Run in interactive mode if requested
    if args.interactive:
        run_interactive_mode(config)
        return
    
    # Handle input file requirement for certain operations
    input_file = None
    if args.command in ["classify", "export_excel", "simplify"]:
        if not args.input_file:
            display_error(f"--input_file is required for the '{args.command}' command")
            return
        input_file = args.input_file
        if not os.path.exists(input_file):
            display_error(f"Input file not found: {input_file}")
            return
    
    # Execute the requested operation
    result = execute_operation(args.command, config, input_file, args.force_classify)
    
    if result:
        console.print("\n[bold green]🎉 Operation completed successfully![/bold green]")
    else:
        console.print("\n[bold red]❌ Operation failed or was cancelled.[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
