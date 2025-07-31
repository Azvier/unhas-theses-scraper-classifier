"""
Classification service with improved architecture and error handling.

This module provides a clean, maintainable service for classifying
thesis abstracts using AI.
"""

import json
import os
import time
from typing import Dict, Any, List
from dataclasses import dataclass

import google.generativeai as genai

from ..core.abstractions import IClassificationService, ClassificationResult, ProcessingResult, ProcessingStatus, ClassificationError
from ..core.utils import FileNameExtractor, FileNameGenerator, PathManager, PerformanceTimer
from ..config.service import ApplicationConfig


@dataclass
class ThesisItem:
    """Container for thesis classification data."""
    id: str
    title: str
    abstract: str
    original_data: Dict[str, Any]


class ClassificationService(IClassificationService):
    """Service for AI-powered thesis classification."""
    
    def __init__(self, config: ApplicationConfig):
        """
        Initialize classification service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self._configure_api()
        self.model = genai.GenerativeModel(config.api.gemini_model)
    
    def _configure_api(self) -> None:
        """Configure the Gemini API."""
        if not self.config.api.google_api_key:
            raise ClassificationError(
                "Google API key not configured. Please set GOOGLE_API_KEY environment "
                "variable or add it to your configuration file."
            )
        
        genai.configure(api_key=self.config.api.google_api_key)
    
    def classify_thesis(self, title: str, abstract: str) -> ClassificationResult:
        """
        Classify a single thesis.
        
        Args:
            title: Thesis title
            abstract: Thesis abstract
            
        Returns:
            Classification result
        """
        # For single classification, use batch with one item
        results = self.classify_batch([{"title": title, "abstract": abstract}])
        return results[0] if results else ClassificationResult("Classification Failed", "Classification Failed")
    
    def classify_batch(self, theses: List[Dict[str, str]]) -> List[ClassificationResult]:
        """
        Classify a batch of theses.
        
        Args:
            theses: List of thesis dictionaries with 'title' and 'abstract'
            
        Returns:
            List of classification results
        """
        if not theses:
            return []
        
        # Prepare batch for API
        batch_items = []
        for i, thesis in enumerate(theses):
            batch_items.append({
                "id": f"item_{i}",
                "title": thesis.get("title", ""),
                "abstract": thesis.get("abstract", "")
            })
        
        # Generate prompt and call API
        prompt = self._generate_classification_prompt(batch_items)
        
        for attempt in range(self.config.classification.retries):
            try:
                response = self.model.generate_content(prompt)
                
                if not response.text:
                    raise ValueError("API returned empty response")
                
                # Parse response
                cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
                classifications = json.loads(cleaned_text)
                
                # Convert to results
                results = []
                for i, thesis in enumerate(theses):
                    item_id = f"item_{i}"
                    classification = classifications.get(item_id, {})
                    
                    if isinstance(classification, dict):
                        primary = classification.get("primary", "Classification Failed")
                        secondary = classification.get("secondary", "Classification Failed")
                        
                        # Validate categories
                        if (primary in self.config.classification.categories and 
                            secondary in self.config.classification.categories):
                            results.append(ClassificationResult(primary, secondary))
                        else:
                            results.append(ClassificationResult("Classification Failed", "Classification Failed"))
                    else:
                        results.append(ClassificationResult("Classification Failed", "Classification Failed"))
                
                return results
                
            except (json.JSONDecodeError, ValueError) as e:
                if self.config.verbose_logging:
                    print(f"    - Warning: API call failed on attempt {attempt + 1}: {e}")
                
                if attempt < self.config.classification.retries - 1:
                    time.sleep(5)
                else:
                    # Return failed results for all items
                    return [ClassificationResult("Classification Failed", "Classification Failed") for _ in theses]
            
            except Exception as e:
                if self.config.verbose_logging:
                    print(f"    - Unexpected error on attempt {attempt + 1}: {e}")
                
                if attempt < self.config.classification.retries - 1:
                    time.sleep(5)
                else:
                    return [ClassificationResult("Classification Failed", "Classification Failed") for _ in theses]
        
        return [ClassificationResult("Classification Failed", "Classification Failed") for _ in theses]
    
    def _generate_classification_prompt(self, batch_items: List[Dict[str, Any]]) -> str:
        """Generate prompt for classification API call."""
        categories = self.config.classification.categories
        category_list_str = "\n".join([f"- **{cat}**: {desc}" for cat, desc in categories.items()])
        items_to_classify_str = json.dumps(batch_items, indent=2, ensure_ascii=False)
        
        prompt = f'''
You are an expert academic classifier. Your task is to classify each research item into categories based on its title and abstract.

**Categories and Descriptions:**
{category_list_str}

**Instructions:**
1. Analyze the title and abstract for each item in the JSON array below.
2. For each item, determine the PRIMARY focus (most dominant theme) and SECONDARY focus (secondary theme, can be same as primary).
3. Your response MUST be a valid JSON object that maps each 'id' to an object with 'primary' and 'secondary' fields.
4. Both category names MUST be one of these exact strings: {", ".join(categories.keys())}.
5. The secondary focus can be the same as primary if the thesis has only one main focus.
6. Do NOT include any explanations, comments, or markdown formatting (like ```json) in your response.

**Research Items to Classify:**
{items_to_classify_str}

**Required Output Format (JSON object):**
{{
  "id_1": {{
    "primary": "CategoryName",
    "secondary": "CategoryName"
  }},
  "id_2": {{
    "primary": "CategoryName", 
    "secondary": "CategoryName"
  }},
  ...
}}
'''
        return prompt


class ThesisClassificationService:
    """High-level service for classifying thesis files."""
    
    def __init__(self, config: ApplicationConfig):
        """
        Initialize thesis classification service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.classification_service = ClassificationService(config)
    
    def classify_theses_file(self, input_filename: str, force_default_categories: bool = False) -> ProcessingResult:
        """
        Classify theses from a JSON file.
        
        Args:
            input_filename: Path to input JSON file
            force_default_categories: Whether to bypass category validation
            
        Returns:
            Processing result with output file path
        """
        with PerformanceTimer("Thesis classification"):
            try:
                # Validate configuration
                if not self._validate_classification_config(force_default_categories):
                    return ProcessingResult(
                        status=ProcessingStatus.FAILED,
                        error_message="Classification blocked due to default categories"
                    )
                
                # Load input data
                try:
                    with open(input_filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    return ProcessingResult(
                        status=ProcessingStatus.FAILED,
                        error_message=f"Input file '{input_filename}' not found"
                    )
                
                # Prepare items for classification
                items_to_classify = self._prepare_classification_items(data)
                
                if not items_to_classify:
                    return ProcessingResult(
                        status=ProcessingStatus.COMPLETED,
                        output_file=input_filename,
                        metadata={"message": "All items already classified"}
                    )
                
                # Show classification start message
                print(f"🤖 Starting classification of {len(items_to_classify)} items...")
                
                # Classify in batches
                self._classify_items_in_batches(items_to_classify)
                
                # Save results
                output_file = self._save_classified_data(data, input_filename)
                
                return ProcessingResult(
                    status=ProcessingStatus.COMPLETED,
                    output_file=output_file,
                    metadata={
                        "classified_count": len(items_to_classify),
                        "total_items": self._count_total_items(data)
                    }
                )
                
            except Exception as e:
                error_msg = f"Classification failed: {e}"
                if self.config.verbose_logging:
                    print(f"❌ {error_msg}")
                
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    error_message=error_msg
                )
    
    def _validate_classification_config(self, force_default_categories: bool = False) -> bool:
        """Validate classification configuration."""
        categories = self.config.classification.categories
        
        if not categories:
            raise ClassificationError("No classification categories defined")
        
        for category, description in categories.items():
            if not description.strip():
                raise ClassificationError(f"Empty description for category: {category}")
        
        # Check if user has confirmed custom categories
        if not self.config.classification.user_defined_categories and not force_default_categories:
            from rich.console import Console
            console = Console()
            
            console.print("\n[red]❌ CLASSIFICATION BLOCKED[/red]")
            console.print("[yellow]Classification categories have not been confirmed as customized![/yellow]")
            console.print("\n[cyan]🔧 REQUIRED ACTIONS:[/cyan]")
            console.print("1. Review and customize the 'classification_categories' section in config.yaml")
            console.print("2. Set 'user_defined_categories: true' in config.yaml to confirm customization")
            console.print("3. Ensure categories use domain-specific terminology for your field")
            console.print("\n[dim]💡 Why? Generic categories lead to poor classification accuracy.[/dim]")
            console.print("[dim]   Custom categories tailored to your field produce better results.[/dim]")
            console.print("\n[green]📝 Run 'python main.py validate-config' for interactive setup.[/green]")
            console.print("[cyan]🧪 For testing: Use --force-classify to bypass this check[/cyan]")
            
            return False
        elif not self.config.classification.user_defined_categories and force_default_categories:
            from rich.console import Console
            console = Console()
            console.print("\n[yellow]⚠️  Using default categories for testing (accuracy may be lower)[/yellow]")
        
        return True
    
    def _prepare_classification_items(self, data: Dict[str, Any]) -> List[ThesisItem]:
        """Prepare items that need classification."""
        items = []
        item_id_counter = 0
        
        for year, theses in data.items():
            for title, details in theses.items():
                # Check if already classified
                if self._is_already_classified(details):
                    continue
                
                abstract = details.get("abstract", "") or ""
                if "LIHAT DI FULL TEXT" in abstract.upper():
                    abstract = ""
                
                items.append(ThesisItem(
                    id=f"task_{item_id_counter}",
                    title=title,
                    abstract=abstract,
                    original_data=details
                ))
                item_id_counter += 1
        
        return items
    
    def _is_already_classified(self, details: Dict[str, Any]) -> bool:
        """Check if thesis is already classified."""
        study_focus = details.get("study_focus")
        
        if isinstance(study_focus, dict) and "primary" in study_focus:
            return True  # New format classification exists
        elif isinstance(study_focus, str) and study_focus != "Classification Failed":
            # Convert old format to new format
            details["study_focus"] = {
                "primary": study_focus,
                "secondary": study_focus
            }
            return True
        
        return False
    
    def _classify_items_in_batches(self, items: List[ThesisItem]) -> None:
        """Classify items in batches with progress tracking."""
        batch_size = self.config.classification.batch_size
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        print(f"📦 Processing {len(items)} items in {total_batches} batches...")
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_number = i // batch_size + 1
            
            # Show progress
            print(f"⚡ Processing batch {batch_number}/{total_batches} ({len(batch)} items)...")
            
            # Prepare batch for classification
            thesis_data = [{"title": item.title, "abstract": item.abstract} for item in batch]
            
            # Classify batch
            results = self.classification_service.classify_batch(thesis_data)
            
            # Apply results to original data
            for item, result in zip(batch, results):
                if result.primary_focus != "Classification Failed":
                    item.original_data["study_focus"] = {
                        "primary": result.primary_focus,
                        "secondary": result.secondary_focus
                    }
                else:
                    item.original_data["study_focus"] = "Classification Failed"
            
            # Show batch completion
            successful = sum(1 for r in results if r.primary_focus != "Classification Failed")
            print(f"✅ Batch {batch_number} completed: {successful}/{len(results)} successful")
        
        print(f"🎯 Classification processing completed for all {len(items)} items")
    
    def _save_classified_data(self, data: Dict[str, Any], input_filename: str) -> str:
        """Save classified data to file."""
        from ..core.abstractions import OperationType
        
        # Extract faculty/major from filename
        faculty, major = FileNameExtractor.extract_faculty_major_from_filename(input_filename)
        
        if faculty and major:
            filename = FileNameGenerator.generate_filename(
                OperationType.CLASSIFY, faculty, major, extension="json"
            )
        else:
            # Fallback to generic name
            filename = FileNameGenerator.generate_filename(
                OperationType.CLASSIFY, "unhas", "repository", extension="json"
            )
        
        output_file = PathManager.resolve_output_path(self.config.processing.output_dir, filename)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"💾 Classification results saved to: {os.path.basename(output_file)}")
        
        return output_file
    
    def _count_total_items(self, data: Dict[str, Any]) -> int:
        """Count total items in data."""
        return sum(len(theses) for theses in data.values())
    
    def classify_repository_file(self, input_file: str) -> ProcessingResult:
        """
        Classify a repository JSON file.
        
        Args:
            input_file: Path to input JSON file
            
        Returns:
            ProcessingResult with classified data
        """
        return self.classify_theses_file(input_file)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # AI service doesn't need cleanup
        pass
