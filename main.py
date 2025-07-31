"""
UNHAS Theses Scraper - Clean Main Entry Point

Main entry point for the UNHAS Theses Scraper application.
Uses clean architecture with proper separation of concerns.
"""

import sys
import argparse
from src.core.orchestrator import ApplicationOrchestrator


def create_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="UNHAS Theses Scraper and Classifier - Refactored Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python main.py --interactive
  
  # Run full pipeline
  python main.py all
  
  # Scrape specific faculty/major
  python main.py scrape --faculty "Fakultas Teknik" --major "Teknik Elektro"
  
  # Classify existing data
  python main.py classify --input output/data.json
  
  # Export to Excel
  python main.py export_excel --input output/classified_data.json
  
  # Create simplified JSON
  python main.py simplify --input output/classified_data.json
  
  # Discovery mode
  python main.py discover
        """
    )
    
    parser.add_argument('command', nargs='?', default='interactive',
                       choices=['all', 'scrape', 'classify', 'export_excel', 'simplify', 'discover', 'interactive'],
                       help='Command to execute')
    parser.add_argument('--interactive', action='store_true',
                       help='Run in interactive mode')
    parser.add_argument('--config', default='config.yaml',
                       help='Configuration file path')
    parser.add_argument('--faculty', help='Faculty name or key')
    parser.add_argument('--major', help='Major name or key')
    parser.add_argument('--input', help='Input file path')
    parser.add_argument('--no-headless', action='store_true',
                       help='Run browser in non-headless mode')
    
    return parser


def main():
    """
    Main entry point for the UNHAS Theses Scraper application.
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle interactive mode or specific commands
    if args.interactive or args.command == 'interactive':
        app = ApplicationOrchestrator(config_path=args.config)
        success = app.run_interactive()
        app.cleanup()
        return success
    else:
        # Handle CLI commands
        app = ApplicationOrchestrator(config_path=args.config)
        if not app.initialize():
            return False
            
        try:
            if args.command == 'discover':
                success = app.run_discovery()
            elif args.command == 'scrape':
                result = app.run_scraping(args.faculty, args.major)
                success = result.success
            elif args.command == 'classify':
                result = app.run_classification(args.input)
                success = result.success
            elif args.command == 'export_excel':
                result = app.run_excel_export(args.input)
                success = result.success
            elif args.command == 'simplify':
                result = app.run_simplification(args.input)
                success = result.success
            elif args.command == 'all':
                success = app.run_complete_pipeline(args.faculty, args.major)
            else:
                parser.print_help()
                return False
                
            return success
        finally:
            app.cleanup()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
