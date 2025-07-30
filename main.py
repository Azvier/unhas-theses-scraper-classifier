

import argparse
import os

from src.classification.classifier import classify_theses
from src.processing.data_processor import (
    convert_json_to_excel, simplify_repository_data)
from src.scraping.scraper import scrape_repository

def main():
    # The script is expected to be run from the project root directory
    # using `python -m src.unhas_theses_scraper.main`
    project_root = os.getcwd()

    parser = argparse.ArgumentParser(description="UNHAS Statistics Theses Scraper and Classifier.")
    parser.add_argument(
        "command",
        choices=["scrape", "classify", "simplify", "export_excel", "all"],
        help="The command to execute."
    )
    parser.add_argument(
        "--input_file",
        type=str,
        help="Path to the input JSON file (relative to project root) for classification, simplification, or export."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="output",
        help="Directory to save output files (relative to project root). Defaults to 'output'."
    )

    args = parser.parse_args()

    # Create absolute paths
    abs_output_dir = os.path.join(project_root, args.output_dir)
    abs_input_file = os.path.join(project_root, args.input_file) if args.input_file else None

    # Ensure output directory exists
    os.makedirs(abs_output_dir, exist_ok=True)

    if args.command == "all":
        print("--- Running all steps: Scrape -> Classify -> Export Excel & Simplify ---")
        # 1. Scrape
        scraped_file = scrape_repository(abs_output_dir)
        if not scraped_file:
            print("Scraping failed. Aborting.")
            return
        print(f"\n--- Scraping finished. Output at: {scraped_file} ---")

        # 2. Classify
        classified_file = classify_theses(scraped_file, abs_output_dir)
        if not classified_file:
            print("Classification failed. Aborting.")
            return
        print(f"\n--- Classification finished. Output at: {classified_file} ---")

        # 3. Post-processing
        print("\n--- Starting post-processing steps ---")
        excel_file = convert_json_to_excel(classified_file, abs_output_dir)
        simplified_file = simplify_repository_data(classified_file, abs_output_dir)
        
        if excel_file:
            print(f"--- Excel export finished. Output at: {excel_file} ---")
        if simplified_file:
            print(f"--- Simplification finished. Output at: {simplified_file} ---")

    elif args.command == "scrape":
        scrape_repository(abs_output_dir)

    elif args.command == "classify":
        if not abs_input_file:
            parser.error("--input_file is required for the 'classify' command.")
        classify_theses(abs_input_file, abs_output_dir)

    elif args.command == "simplify":
        if not abs_input_file:
            parser.error("--input_file is required for the 'simplify' command.")
        simplify_repository_data(abs_input_file, abs_output_dir)

    elif args.command == "export_excel":
        if not abs_input_file:
            parser.error("--input_file is required for the 'export_excel' command.")
        convert_json_to_excel(abs_input_file, abs_output_dir)

    print("\n✅ Done.")


if __name__ == "__main__":
    main()

