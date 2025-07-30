# UNHAS Statistics Theses Scraper & Classifier

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A command-line tool to scrape, classify, and process undergraduate thesis data from the Hasanuddin University (UNHAS) Statistics Department repository.

## 🚀 Features

- **Data Scraping**: Automatically scrapes thesis metadata, including titles, authors, and abstracts, from the [UNHAS Repository](https://repository.unhas.ac.id/view/divisions/statistika/).
- **AI-Powered Classification**: Uses the Google Gemini API to intelligently classify each thesis into predefined statistical categories (e.g., *Regression*, *Time Series Analysis*, *Machine Learning*).
- **Multiple Output Formats**: Exports the processed data into both JSON and Excel formats for further analysis.
- **Modular Architecture**: Built with a clear and modular structure, separating scraping, classification, and data processing logic.
- **CLI Interface**: Provides a user-friendly command-line interface to run individual tasks or the entire pipeline.

## 🏛️ Architecture and Workflow

The project follows a sequential pipeline:

1.  **Scraping**: The `scraper.py` module uses `selenium` to navigate the UNHAS repository, extract thesis data year by year, and save it into a structured JSON file.
2.  **Classification**: The `classifier.py` module reads the scraped data, sends the title and abstract of each thesis to the Gemini API for categorization, and saves the enriched data in a new JSON file.
3.  **Processing**: The `data_processor.py` module provides utilities to:
    - Convert the final classified JSON data into a user-friendly Excel file.
    - Generate a simplified JSON file containing only the essential fields (title, abstract, study focus).

## 📂 Project Structure

```
unhas-statistics-theses-scraping/
├── .gitignore
├── main.py
├── pdm.lock
├── pyproject.toml
├── readme-instruction.md
├── README.md
├── notebooks/
│   └── legacy/
│       └── scraping.ipynb
├── output/
│   └── (Generated files will appear here)
└── src/
    ├── classification/
    │   └── classifier.py   # AI-based thesis classification
    ├── processing/
    │   └── data_processor.py # Data export (JSON, Excel)
    └── scraping/
        └── scraper.py      # Web scraping logic
```

-   **`main.py`**: The main entry point for the command-line interface.
-   **`src/scraping`**: Contains the web scraping logic.
-   **`src/classification`**: Handles the AI-powered classification of theses.
-   **`src/processing`**: Includes functions for data conversion and simplification.
-   **`output/`**: The default directory for all generated output files.

## 🏁 Getting Started

### Prerequisites

-   Python 3.12+
-   [PDM](https://pdm-project.org/) for package management.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/unhas-statistics-theses-scraping.git
    cd unhas-statistics-theses-scraping
    ```

2.  **Install dependencies using PDM:**
    ```bash
    pdm install
    ```

3.  **Set up your API Key:**
    - Create a file named `.env` in the project root.
    - Add your Google Gemini API key to it:
      ```
      GOOGLE_API_KEY="YOUR_API_KEY_HERE"
      ```

## ⚙️ Usage

The script is run via `main.py` and accepts several commands.

### Run the Full Pipeline

To execute the entire workflow (scrape, classify, and export), run:

```bash
pdm run python main.py all
```

This will create four output files in the `output/` directory:
- `unhas_repository_[timestamp].json` (raw scraped data)
- `unhas_repository_classified_[timestamp].json` (data with classification)
- `unhas_repository_classified_[timestamp].xlsx` (classified data in Excel format)
- `unhas_repository_simplified_[timestamp].json` (simplified data)

### Run Individual Commands

You can also run each step individually.

-   **Scrape Data:**
    ```bash
    pdm run python main.py scrape
    ```

-   **Classify Data:**
    *(Requires a scraped JSON file as input)*
    ```bash
    pdm run python main.py classify --input_file "output/unhas_repository_[timestamp].json"
    ```

-   **Export to Excel:**
    *(Requires a classified JSON file as input)*
    ```bash
    pdm run python main.py export_excel --input_file "output/unhas_repository_classified_[timestamp].json"
    ```

-   **Simplify Data:**
    *(Requires a classified JSON file as input)*
    ```bash
    pdm run python main.py simplify --input_file "output/unhas_repository_classified_[timestamp].json"
    ```

## 📝 Note on Data

This repository contains the code to scrape and process data. The actual thesis data is not included but can be fully reproduced by running the scraping script. The final output will be a clean, classified, and structured dataset ready for analysis.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
