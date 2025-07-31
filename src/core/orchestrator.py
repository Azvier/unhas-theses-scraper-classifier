"""
Main application orchestrator for the UNHAS Theses Scraper.

This module provides the main application coordination and orchestration
layer following the orchestrator pattern. It coordinates all services
and provides the main entry point for the application.
"""

import os
import sys
from typing import Optional, Dict, Any

from ..config.service import ConfigurationService, ApplicationConfig
from ..cli.service import RichUserInterface, InteractiveFlowOrchestrator
from ..discovery.service import UNHASDiscoveryService
from ..scraping.service import UNHASScrapingService
from ..classification.service import ThesisClassificationService
from ..processing.service import DataProcessingOrchestrator
from ..core.abstractions import (
    IUserInterface, 
    OperationType,
    ProcessingResult,
    ProcessingStatus
)


class ApplicationOrchestrator:
    """
    Main application orchestrator that coordinates all services.
    
    This class follows the orchestrator pattern to coordinate the workflow
    between different services without tight coupling.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the application orchestrator.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config: Optional[ApplicationConfig] = None
        self.ui: IUserInterface = RichUserInterface()
        
        # Service instances (initialized lazily)
        self._discovery_service: Optional[UNHASDiscoveryService] = None
        self._scraping_service: Optional[UNHASScrapingService] = None
        self._classification_service: Optional[ThesisClassificationService] = None
        self._processing_service: Optional[DataProcessingOrchestrator] = None
    
    def initialize(self) -> bool:
        """
        Initialize the application and load configuration.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            config_service = ConfigurationService()
            self.config = config_service.load_config(self.config_path)
            
            # Ensure output directory exists
            os.makedirs(self.config.processing.output_dir, exist_ok=True)
            
            return True
            
        except Exception as e:
            self.ui.display_error(f"Failed to initialize application: {e}")
            return False
    
    def run_interactive(self) -> bool:
        """
        Run the application in interactive mode.
        
        Returns:
            True if operation completed successfully, False otherwise
        """
        if not self.initialize():
            return False
        
        try:
            orchestrator = InteractiveFlowOrchestrator(self.ui, self.config)
            user_choices = orchestrator.run_interactive_mode()
            
            if user_choices.get("cancelled", False):
                return False
            
            return self._execute_operation(user_choices)
            
        except KeyboardInterrupt:
            self.ui.display_warning("\nOperation cancelled by user")
            return False
        except Exception as e:
            self.ui.display_error(f"Interactive mode failed: {e}")
            return False
    
    def run_scraping(self, faculty: str, major: str) -> ProcessingResult:
        """
        Run scraping operation for specific faculty/major.
        
        Args:
            faculty: Faculty key
            major: Major key
            
        Returns:
            ProcessingResult with operation details
        """
        try:
            service = self._get_scraping_service()
            
            self.ui.display_info(f"Starting scraping: {faculty} - {major}")
            
            # Update config with target
            self.config.scraping.target_faculty = faculty
            self.config.scraping.target_major = major
            
            result = service.scrape_faculty_major(faculty, major)
            
            if result.success:
                self.ui.display_success(f"Scraping completed: {result.output_file}")
            else:
                self.ui.display_error(f"Scraping failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            error_msg = f"Scraping operation failed: {e}"
            self.ui.display_error(error_msg)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=error_msg
            )
    
    def run_classification(self, input_file: str) -> ProcessingResult:
        """
        Run classification operation on scraped data.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            ProcessingResult with operation details
        """
        try:
            service = self._get_classification_service()
            
            self.ui.display_info(f"Starting classification: {os.path.basename(input_file)}")
            
            result = service.classify_repository_file(input_file)
            
            if result.success:
                self.ui.display_success(f"Classification completed: {result.output_file}")
            else:
                self.ui.display_error(f"Classification failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            error_msg = f"Classification operation failed: {e}"
            self.ui.display_error(error_msg)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=error_msg
            )
    
    def run_excel_export(self, input_file: str) -> ProcessingResult:
        """
        Run Excel export operation.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            ProcessingResult with operation details
        """
        try:
            service = self._get_processing_service()
            
            self.ui.display_info(f"Starting Excel export: {os.path.basename(input_file)}")
            
            result = service.export_to_excel(input_file)
            
            if result.success:
                self.ui.display_success(f"Excel export completed: {result.output_file}")
            else:
                self.ui.display_error(f"Excel export failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            error_msg = f"Excel export operation failed: {e}"
            self.ui.display_error(error_msg)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=error_msg
            )
    
    def run_simplification(self, input_file: str) -> ProcessingResult:
        """
        Run data simplification operation.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            ProcessingResult with operation details
        """
        try:
            service = self._get_processing_service()
            
            self.ui.display_info(f"Starting simplification: {os.path.basename(input_file)}")
            
            result = service.create_simplified_data(input_file)
            
            if result.success:
                self.ui.display_success(f"Simplification completed: {result.output_file}")
            else:
                self.ui.display_error(f"Simplification failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            error_msg = f"Simplification operation failed: {e}"
            self.ui.display_error(error_msg)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                error_message=error_msg
            )
    
    def run_complete_pipeline(self, faculty: str, major: str) -> bool:
        """
        Run the complete pipeline: scrape -> classify -> export -> simplify.
        
        Args:
            faculty: Faculty key
            major: Major key
            
        Returns:
            True if all operations successful, False otherwise
        """
        try:
            self.ui.display_info("Starting complete pipeline")
            
            # Step 1: Scraping
            scrape_result = self.run_scraping(faculty, major)
            if not scrape_result.success:
                return False
            
            # Step 2: Classification
            classify_result = self.run_classification(scrape_result.output_file)
            if not classify_result.success:
                return False
            
            # Step 3: Excel Export
            excel_result = self.run_excel_export(classify_result.output_file)
            if not excel_result.success:
                self.ui.display_warning("Excel export failed, but continuing...")
            
            # Step 4: Simplification
            simplify_result = self.run_simplification(classify_result.output_file)
            if not simplify_result.success:
                self.ui.display_warning("Simplification failed, but pipeline mostly completed")
            
            self.ui.display_success("Complete pipeline finished successfully")
            return True
            
        except Exception as e:
            self.ui.display_error(f"Pipeline failed: {e}")
            return False
    
    def run_discovery(self) -> bool:
        """
        Run faculty/major discovery and update configuration.
        
        Returns:
            True if discovery completed successfully, False otherwise
        """
        try:
            self.ui.display_info("Starting faculty/major discovery...")
            
            discovery_service = self._get_discovery_service()
            discovered_data = discovery_service.discover_faculties_and_majors()
            
            if not discovered_data:
                self.ui.display_error("Discovery failed - no data found")
                return False
            
            # Update configuration with discovered data
            config_service = ConfigurationService()
            self.config.faculties = discovered_data
            config_service.save_config(self.config, self.config_path)
            
            # Calculate total majors across all faculties
            total_majors = sum(len(faculty_data.get('majors', {})) for faculty_data in discovered_data.values())
            
            self.ui.display_success(f"Discovery completed! Found {len(discovered_data)} faculties and {total_majors} majors")
            self.ui.display_info(f"Configuration updated: {self.config_path}")
            
            return True
            
        except Exception as e:
            self.ui.display_error(f"Discovery failed: {e}")
            return False
    
    def _execute_operation(self, user_choices: Dict[str, Any]) -> bool:
        """Execute the operation based on user choices."""
        operation = user_choices["operation"]
        
        try:
            if operation == "scrape":
                result = self.run_scraping(
                    user_choices["faculty_key"],
                    user_choices["major_key"]
                )
                return result.success
            
            elif operation == "classify":
                result = self.run_classification(user_choices["input_file"])
                return result.success
            
            elif operation == "export_excel":
                result = self.run_excel_export(user_choices["input_file"])
                return result.success
            
            elif operation == "simplify":
                result = self.run_simplification(user_choices["input_file"])
                return result.success
            
            elif operation == "all":
                result = self.run_complete_pipeline(
                    user_choices["faculty_key"],
                    user_choices["major_key"]
                )
                return result
            
            else:
                self.ui.display_error(f"Unknown operation: {operation}")
                return False
                
        except Exception as e:
            self.ui.display_error(f"Operation execution failed: {e}")
            return False
    
    def _get_discovery_service(self) -> UNHASDiscoveryService:
        """Get or create discovery service instance."""
        if self._discovery_service is None:
            self._discovery_service = UNHASDiscoveryService(
                headless=self.config.scraping.headless_browser,
                verbose=self.config.verbose_logging
            )
        return self._discovery_service
    
    def _get_scraping_service(self) -> UNHASScrapingService:
        """Get or create scraping service instance."""
        if self._scraping_service is None:
            self._scraping_service = UNHASScrapingService(self.config)
        return self._scraping_service
    
    def _get_classification_service(self) -> ThesisClassificationService:
        """Get or create classification service instance."""
        if self._classification_service is None:
            self._classification_service = ThesisClassificationService(self.config)
        return self._classification_service
    
    def _get_processing_service(self) -> DataProcessingOrchestrator:
        """Get or create processing service instance."""
        if self._processing_service is None:
            self._processing_service = DataProcessingOrchestrator(self.config)
        return self._processing_service
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up web drivers and other resources
            if self._discovery_service:
                self._discovery_service.cleanup()
            if self._scraping_service:
                self._scraping_service.cleanup()
        except Exception as e:
            self.ui.display_warning(f"Cleanup warning: {e}")


def main():
    """
    Main entry point for the application.
    
    This function provides the main entry point and handles
    command-line arguments and overall application flow.
    """
    try:
        # Initialize application
        app = ApplicationOrchestrator()
        
        # Check for command line arguments
        if len(sys.argv) > 1:
            # Handle command line mode (future enhancement)
            app.ui.display_warning("Command line mode not yet implemented")
            app.ui.display_info("Running in interactive mode...")
        
        # Run interactive mode
        success = app.run_interactive()
        
        # Cleanup
        app.cleanup()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
