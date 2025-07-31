"""
Data processing service with improved architecture and error handling.

This module provides clean, maintainable services for converting
and processing thesis data into various formats.
"""

import json
import pandas as pd
from typing import Dict, Any, List

from ..core.abstractions import (
    IExcelExporter, 
    IDataSimplifier,
    ProcessingResult, 
    ProcessingStatus,
    OperationType
)
from ..core.utils import TextSanitizer, FileNameExtractor, FileNameGenerator, PathManager, PerformanceTimer
from ..config.service import ApplicationConfig


class ExcelExportService(IExcelExporter):
    """Service for converting JSON data to Excel format."""
    
    def __init__(self, config: ApplicationConfig):
        """
        Initialize Excel export service.
        
        Args:
            config: Application configuration
        """
        self.config = config
    
    def convert_to_excel(self, input_file: str) -> ProcessingResult:
        """
        Convert JSON data to Excel format.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            Processing result with output file path
        """
        with PerformanceTimer("Excel export"):
            try:
                # Load input data
                try:
                    with open(input_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    return ProcessingResult(
                        status=ProcessingStatus.FAILED,
                        error_message=f"Input file '{input_file}' not found"
                    )
                
                # Convert to DataFrame
                df = self._convert_to_dataframe(data)
                
                # Sanitize data for Excel compatibility
                df = self._sanitize_dataframe(df)
                
                # Generate output filename
                output_file = self._generate_output_filename(input_file, "xlsx")
                
                # Export to Excel
                df.to_excel(output_file, index=False)
                
                if self.config.verbose_logging:
                    print(f"✅ Data exported to '{output_file}'")
                
                return ProcessingResult(
                    status=ProcessingStatus.COMPLETED,
                    output_file=output_file,
                    metadata={
                        "total_rows": len(df),
                        "columns": list(df.columns)
                    }
                )
                
            except Exception as e:
                error_msg = f"Excel export failed: {e}"
                if self.config.verbose_logging:
                    print(f"❌ {error_msg}")
                
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error_message=error_msg
                )
    
    def _convert_to_dataframe(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Convert JSON data to pandas DataFrame."""
        rows = []
        
        for year, theses in data.items():
            for title, details in theses.items():
                row = {'year': year, 'title': title}
                
                # Handle study_focus - both old and new format
                study_focus = details.get('study_focus')
                if isinstance(study_focus, dict):
                    # New format with primary/secondary
                    row['primary_focus'] = study_focus.get('primary', 'Not Available')
                    row['secondary_focus'] = study_focus.get('secondary', 'Not Available')
                    row['study_focus'] = study_focus.get('primary', 'Not Available')  # Backward compatibility
                elif isinstance(study_focus, str):
                    # Old format or failed classification
                    row['primary_focus'] = study_focus
                    row['secondary_focus'] = study_focus if study_focus != "Classification Failed" else "Not Available"
                    row['study_focus'] = study_focus  # Backward compatibility
                else:
                    # No classification
                    row['primary_focus'] = 'Not Available'
                    row['secondary_focus'] = 'Not Available'
                    row['study_focus'] = 'Not Available'
                
                # Add other details
                for key, value in details.items():
                    if key != 'study_focus':  # Already handled above
                        row[key] = value
                
                rows.append(row)
        
        # Create DataFrame and reorder columns logically
        df = pd.DataFrame(rows)
        
        # Define preferred column order
        preferred_columns = [
            'year', 'title', 'author', 'primary_focus', 'secondary_focus', 
            'study_focus', 'abstract', 'item_type', 'date_deposited', 
            'last_modified', 'url'
        ]
        
        # Reorder columns, keeping any additional columns at the end
        existing_columns = df.columns.tolist()
        ordered_columns = [col for col in preferred_columns if col in existing_columns]
        remaining_columns = [col for col in existing_columns if col not in preferred_columns]
        final_columns = ordered_columns + remaining_columns
        
        return df[final_columns]
    
    def _sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sanitize DataFrame for Excel compatibility."""
        # Sanitize all text columns to prevent XML parsing errors
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns
                df[col] = df[col].apply(TextSanitizer.sanitize_xml_text)
        
        return df
    
    def _generate_output_filename(self, input_file: str, extension: str) -> str:
        """Generate output filename for Excel export."""
        # Extract faculty/major from input filename
        faculty, major = FileNameExtractor.extract_faculty_major_from_filename(input_file)
        
        if faculty and major:
            filename = FileNameGenerator.generate_filename(
                OperationType.EXPORT_EXCEL, faculty, major, extension=extension
            )
        else:
            # Fallback to generic name
            filename = FileNameGenerator.generate_filename(
                OperationType.EXPORT_EXCEL, "unhas", "repository", extension=extension
            )
        
        return PathManager.resolve_output_path(self.config.processing.output_dir, filename)


class DataSimplificationService(IDataSimplifier):
    """Service for creating simplified versions of thesis data."""
    
    def __init__(self, config: ApplicationConfig):
        """
        Initialize data simplification service.
        
        Args:
            config: Application configuration
        """
        self.config = config
    
    def simplify_data(self, input_file: str) -> ProcessingResult:
        """
        Create simplified version of data.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            Processing result with output file path
        """
        with PerformanceTimer("Data simplification"):
            try:
                # Load input data
                try:
                    with open(input_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    return ProcessingResult(
                        status=ProcessingStatus.FAILED,
                        error_message=f"Input file '{input_file}' not found"
                    )
                
                # Create simplified data
                simplified_data = self._create_simplified_data(data)
                
                # Generate output filename
                output_file = self._generate_output_filename(input_file)
                
                # Save simplified data
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(simplified_data, f, indent=4, ensure_ascii=False)
                
                if self.config.verbose_logging:
                    print(f"✅ Successfully created simplified JSON file at: {output_file}")
                
                return ProcessingResult(
                    status=ProcessingStatus.COMPLETED,
                    output_file=output_file,
                    metadata={
                        "total_items": len(simplified_data),
                        "format": "simplified_json"
                    }
                )
                
            except Exception as e:
                error_msg = f"Data simplification failed: {e}"
                if self.config.verbose_logging:
                    print(f"❌ {error_msg}")
                
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error_message=error_msg
                )
    
    def _create_simplified_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create simplified flat list from nested data."""
        simplified_list = []
        
        # Iterate through the top-level keys (e.g., '2002', 'NULL')
        for year_key in data:
            # Iterate through each paper's title and its details
            for title, details in data[year_key].items():
                new_entry = {
                    'title': title,
                    'abstract': details.get('abstract', 'Not Available'),
                }
                
                # Handle study_focus - both old and new format
                study_focus = details.get('study_focus', 'Not Available')
                if isinstance(study_focus, dict):
                    # New format with primary/secondary
                    new_entry['primary_focus'] = study_focus.get('primary', 'Not Available')
                    new_entry['secondary_focus'] = study_focus.get('secondary', 'Not Available')
                elif isinstance(study_focus, str):
                    # Old format or failed classification
                    new_entry['primary_focus'] = study_focus
                    new_entry['secondary_focus'] = study_focus if study_focus != "Classification Failed" else "Not Available"
                else:
                    # No classification
                    new_entry['primary_focus'] = 'Not Available'
                    new_entry['secondary_focus'] = 'Not Available'
                
                simplified_list.append(new_entry)
        
        return simplified_list
    
    def _generate_output_filename(self, input_file: str) -> str:
        """Generate output filename for simplified data."""
        # Extract faculty/major from input filename
        faculty, major = FileNameExtractor.extract_faculty_major_from_filename(input_file)
        
        if faculty and major:
            filename = FileNameGenerator.generate_filename(
                OperationType.SIMPLIFY, faculty, major, extension="json"
            )
        else:
            # Fallback to generic name
            filename = FileNameGenerator.generate_filename(
                OperationType.SIMPLIFY, "unhas", "repository", extension="json"
            )
        
        return PathManager.resolve_output_path(self.config.processing.output_dir, filename)


class DataProcessingOrchestrator:
    """Orchestrator for coordinating multiple data processing operations."""
    
    def __init__(self, config: ApplicationConfig):
        """
        Initialize data processing orchestrator.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.excel_service = ExcelExportService(config)
        self.simplification_service = DataSimplificationService(config)
    
    def process_all_formats(self, input_file: str) -> Dict[str, ProcessingResult]:
        """
        Process data into all enabled formats.
        
        Args:
            input_file: Path to input classified JSON file
            
        Returns:
            Dictionary of format names to processing results
        """
        results = {}
        
        if self.config.processing.enable_excel_export:
            if self.config.verbose_logging:
                print("📊 Converting to Excel format...")
            results['excel'] = self.excel_service.convert_to_excel(input_file)
        
        if self.config.processing.enable_simplified_json:
            if self.config.verbose_logging:
                print("📝 Creating simplified JSON...")
            results['simplified'] = self.simplification_service.simplify_data(input_file)
        
        return results
    
    def create_simplified_data(self, input_file: str) -> ProcessingResult:
        """
        Create simplified JSON data from input file.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            Processing result with output file path
        """
        return self.simplification_service.simplify_data(input_file)
    
    def export_to_excel(self, input_file: str) -> ProcessingResult:
        """
        Export data to Excel format.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            Processing result with output file path
        """
        return self.excel_service.convert_to_excel(input_file)
