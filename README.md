# UNHAS Statistics Theses Scraper & Classifier

A command-line tool that automates the collection, classification, and processing of undergraduate thesis data from Hasanuddin University's (UNHAS) digital repository. Features AI-powered thesis categorization using Google's Gemini API and exports data in multiple formats for academic research.

## ✨ Features

- **🎓 Complete Coverage**: Dynamic discovery of all 17 UNHAS faculties and their majors
- **🤖 AI Classification**: Intelligent thesis categorization with primary/secondary focus detection
- **📊 Multiple Formats**: Export to JSON, Excel, and simplified formats
- **🎯 Interactive Mode**: Guided CLI with progress indicators and rich formatting

## 🏗️ Architecture

```
UNHAS Repository → Discovery → Scraping → Raw JSON → AI Classification → Processed Data → Export
```

1. **Dynamic Discovery**: Detects available faculties/majors from university website
2. **Web Scraping**: Extracts thesis metadata using Selenium WebDriver
3. **AI Classification**: Processes abstracts through Google Gemini API
4. **Export Processing**: Generates multiple output formats

## 📁 Project Structure

```
unhas-statistics-theses-scraping/
├── src/
│   ├── cli/interface.py          # Interactive CLI interface
│   ├── config/settings.py        # Configuration management
│   ├── classification/classifier.py # AI-powered classification
│   ├── processing/data_processor.py # Multi-format exports
│   └── scraping/
│       ├── scraper.py            # Core scraping logic
│       └── discovery.py          # Faculty/major discovery
├── main.py                       # CLI application entry point
├── config.yaml                   # Configuration file
└── output/                       # Generated data files
```

## 🚀 Getting Started

### Prerequisites
- **Python 3.12**: Required for optimal performance
- **PDM**: Modern Python dependency manager (`pip install pdm`)
- **Google Gemini API Key**: For AI-powered classification ([Get API Key](https://aistudio.google.com/app/apikey))
- **Chrome/Chromium**: For web scraping automation

### Installation

```bash
# Clone repository
git clone https://github.com/Azvier/unhas-statistics-theses-scraping.git
cd unhas-statistics-theses-scraping

# Install dependencies
pdm install

# Set API key
echo 'GOOGLE_API_KEY="your_api_key_here"' > .env

# Run application
pdm run python main.py --interactive
```

## 📖 Usage

### Interactive Mode (Recommended)
The most user-friendly way to use the application:

```bash
pdm run python main.py --interactive
```

### Command Line Examples
For automation and scripting:

```bash
# Discover available faculties/majors
pdm run python main.py discover

# Full pipeline with specific faculty/major
pdm run python main.py all --faculty "Fakultas Teknik" --major "Teknik Elektro"

# Individual operations
pdm run python main.py scrape --faculty "Fakultas Matematika dan Ilmu Peng. Alam" --major "Statistika"
pdm run python main.py classify --input_file output/scraped_data.json
pdm run python main.py export_excel --input_file output/classified_data.json

# List available options
pdm run python main.py list-faculties
pdm run python main.py list-majors --faculty "Fakultas Teknik"
```

## ⚙️ Configuration

The system uses `config.yaml` with environment variable support:

```yaml
# API Settings
google_api_key: ${GOOGLE_API_KEY}  # Set in .env file
gemini_model: gemini-2.5-pro

# Basic Settings
output_dir: output
headless_browser: true
batch_size: 20
user_defined_categories: false  # Set to true for custom classification

# Custom Classification Categories
# Customize these categories for your specific research domain
classification_categories:
  default:
    Teori: Penelitian yang fokus pada pengembangan teori dan konsep fundamental.
    Aplikasi: Penelitian yang fokus pada penerapan teori untuk memecahkan masalah praktis.
    Eksperimental: Penelitian yang melibatkan eksperimen dan pengujian empiris.
    # Add more categories as needed...
```

**Note**: For domain-specific classification (e.g., statistics), modify the `classification_categories` section with detailed, non-overlapping category definitions to prevent misclassification.

## 📊 Output Formats

### Raw Data
```json
{
  "2023": {
    "Thesis Title": {
      "author": "Student Name",
      "abstract": "Complete abstract...",
      "faculty": "Fakultas Matematika dan Ilmu Peng. Alam",
      "major": "Statistika",
      "url": "https://repository.unhas.ac.id/..."
    }
  }
}
```

### Classified Data
```json
{
  "study_focus": {
    "primary": "Machine Learning",
    "secondary": "Regresi"
  }
}
```

## 🎓 Supported Faculties

All 17 UNHAS faculties are supported through dynamic discovery:
- Fakultas Teknik, Matematika dan Ilmu Peng. Alam, Kedokteran, Farmasi, Hukum
- Fakultas Ekonomi dan Bisnis, Ilmu Kelautan dan Perikanan
- And 10+ more with automatic major detection

## 🛠️ Data Reproducibility

This project is fully reproducible:
- All data scraped from public UNHAS repository
- Automated faculty/major discovery
- API-based classification for consistent results
- No external data dependencies required

## 🤝 Contributing

Contributions welcome! Please feel free to submit pull requests or open issues for bugs, features, or improvements.

**Areas for contribution:**
- Additional university support
- Enhanced classification categories
- New export formats
- Performance optimizations

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: This tool is for academic research. Please comply with university terms of service and use responsibly.
