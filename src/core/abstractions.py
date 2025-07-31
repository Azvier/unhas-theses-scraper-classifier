"""
Core abstractions and interfaces for the UNHAS Theses Scraper.

This module defines the foundational interfaces and abstract base classes
that establish the contracts for various components of the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol
from dataclasses import dataclass
from enum import Enum


class OperationType(Enum):
    """Enumeration of supported operations."""
    SCRAPE = "scrape"
    CLASSIFY = "classify" 
    EXPORT_EXCEL = "export_excel"
    SIMPLIFY = "simplify"
    ALL = "all"


class ProcessingStatus(Enum):
    """Enumeration of processing statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingResult:
    """Result of a processing operation."""
    status: ProcessingStatus
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def success(self) -> bool:
        """Check if the operation was successful."""
        return self.status == ProcessingStatus.COMPLETED


@dataclass
class ScrapingTarget:
    """Target for scraping operations."""
    faculty_key: str
    major_key: str
    faculty_display: str
    major_display: str
    url: str


@dataclass
class ClassificationResult:
    """Result of thesis classification."""
    primary_focus: str
    secondary_focus: str
    confidence: Optional[float] = None


class IWebDriver(Protocol):
    """Protocol for web driver implementations."""
    
    def get(self, url: str) -> None:
        """Navigate to URL."""
        ...
    
    def find_element(self, by: str, value: str) -> Any:
        """Find element by locator."""
        ...
    
    def find_elements(self, by: str, value: str) -> List[Any]:
        """Find elements by locator."""
        ...
    
    def quit(self) -> None:
        """Close the driver."""
        ...


class IDiscoveryService(ABC):
    """Abstract base class for discovery services."""
    
    @abstractmethod
    def discover_faculties(self) -> Dict[str, Dict[str, Any]]:
        """Discover available faculties."""
        pass
    
    @abstractmethod
    def discover_majors_for_faculty(self, faculty_key: str) -> Dict[str, Dict[str, Any]]:
        """Discover majors for a specific faculty."""
        pass


class IScrapingService(ABC):
    """Abstract base class for scraping services."""
    
    @abstractmethod
    def scrape_repository(self, target: ScrapingTarget) -> ProcessingResult:
        """Scrape thesis data from repository."""
        pass
    
    @abstractmethod
    def extract_thesis_data(self, url: str) -> Dict[str, Any]:
        """Extract data from a single thesis page."""
        pass


class IClassificationService(ABC):
    """Abstract base class for classification services."""
    
    @abstractmethod
    def classify_thesis(self, title: str, abstract: str) -> ClassificationResult:
        """Classify a single thesis."""
        pass
    
    @abstractmethod
    def classify_batch(self, theses: List[Dict[str, str]]) -> List[ClassificationResult]:
        """Classify a batch of theses."""
        pass


class IDataProcessor(ABC):
    """Abstract base class for data processing services."""
    
    @abstractmethod
    def process_data(self, input_file: str) -> ProcessingResult:
        """Process data."""
        pass


class IExcelExporter(ABC):
    """Abstract base class for Excel export services."""
    
    @abstractmethod
    def convert_to_excel(self, input_file: str) -> ProcessingResult:
        """Convert JSON data to Excel format."""
        pass


class IDataSimplifier(ABC):
    """Abstract base class for data simplification services."""
    
    @abstractmethod
    def simplify_data(self, input_file: str) -> ProcessingResult:
        """Create simplified version of data."""
        pass


class IConfigurationService(ABC):
    """Abstract base class for configuration services."""
    
    @abstractmethod
    def load_config(self, config_path: str) -> Any:
        """Load configuration from file."""
        pass
    
    @abstractmethod
    def save_config(self, config: Any, config_path: str) -> None:
        """Save configuration to file."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Any) -> bool:
        """Validate configuration."""
        pass


class IUserInterface(ABC):
    """Abstract base class for user interfaces."""
    
    @abstractmethod
    def display_welcome(self) -> None:
        """Display welcome message."""
        pass
    
    @abstractmethod
    def select_faculty_major(self, faculties: Dict[str, Any]) -> tuple:
        """Interactive faculty/major selection."""
        pass
    
    @abstractmethod
    def display_progress(self, operation: str, progress: float) -> None:
        """Display operation progress."""
        pass
    
    @abstractmethod
    def display_error(self, message: str) -> None:
        """Display error message."""
        pass
    
    @abstractmethod
    def display_success(self, message: str) -> None:
        """Display success message."""
        pass
    
    @abstractmethod
    def display_warning(self, message: str) -> None:
        """Display warning message."""
        pass
    
    @abstractmethod
    def display_info(self, message: str) -> None:
        """Display info message."""
        pass


class IFileNameGenerator(ABC):
    """Abstract base class for generating output filenames."""
    
    @abstractmethod
    def generate_filename(self, 
                         operation: OperationType,
                         faculty: str,
                         major: str,
                         timestamp: Optional[str] = None) -> str:
        """Generate filename for operation output."""
        pass


class BusinessLogicError(Exception):
    """Base exception for business logic errors."""
    pass


class ValidationError(BusinessLogicError):
    """Exception for validation errors."""
    pass


class ConfigurationError(BusinessLogicError):
    """Exception for configuration errors."""
    pass


class ScrapingError(BusinessLogicError):
    """Exception for scraping errors."""
    pass


class ClassificationError(BusinessLogicError):
    """Exception for classification errors."""
    pass


class ProcessingError(BusinessLogicError):
    """Exception for data processing errors."""
    pass
