"""Core abstractions and interfaces."""

from .abstractions import (
    IWebDriver,
    IScrapingService,
    IClassificationService, 
    IDataProcessor,
    IExcelExporter,
    IDataSimplifier,
    IDiscoveryService,
    IConfigurationService,
    IUserInterface,
    IFileNameGenerator,
    OperationType,
    ProcessingResult,
    ProcessingStatus,
    BusinessLogicError,
    ValidationError,
    ConfigurationError,
    ScrapingError,
    ClassificationError,
    ProcessingError
)

from .utils import (
    FileNameExtractor,
    TextSanitizer,
    PathManager
)

from .webdriver import (
    WebDriverService,
    ElementLocator
)

__all__ = [
    'IWebDriver',
    'IScrapingService', 
    'IClassificationService',
    'IDataProcessor',
    'IExcelExporter',
    'IDataSimplifier',
    'IDiscoveryService',
    'IConfigurationService',
    'IUserInterface',
    'IFileNameGenerator',
    'OperationType',
    'ProcessingResult',
    'ProcessingStatus',
    'BusinessLogicError',
    'ValidationError',
    'ConfigurationError',
    'ScrapingError',
    'ClassificationError',
    'ProcessingError',
    'FileNameExtractor',
    'TextSanitizer',
    'PathManager',
    'WebDriverService',
    'ElementLocator'
]
