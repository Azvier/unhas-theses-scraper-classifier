
import json
import os
from datetime import datetime
import pandas as pd


def convert_json_to_excel(input_path, output_dir="output"):
    """Converts a classified JSON file to an Excel file."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")
        return None

    rows = []
    for year, theses in data.items():
        for title, details in theses.items():
            row = {'year': year, 'title': title}
            row.update(details)
            rows.append(row)

    df = pd.DataFrame(rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(output_dir, f'unhas_repository_classified_{timestamp}.xlsx')
    os.makedirs(output_dir, exist_ok=True)
    df.to_excel(output_filename, index=False)
    print(f"✅ Data exported to '{output_filename}'")
    return output_filename


def simplify_repository_data(input_path, output_dir="output"):
    """
    Reads a nested JSON repository file, flattens it, and extracts
    only the title, abstract, and study focus for each entry.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")
        return None

    simplified_list = []
    # Iterate through the top-level keys (e.g., '2002', 'NULL')
    for year_key in data:
        # Iterate through each paper's title and its details
        for title, details in data[year_key].items():
            new_entry = {
                'title': title,
                'abstract': details.get('abstract', 'Not Available'),
                'study_focus': details.get('study_focus', 'Not Available')
            }
            simplified_list.append(new_entry)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f'unhas_repository_simplified_{timestamp}.json'
    output_path = os.path.join(output_dir, output_filename)
    os.makedirs(output_dir, exist_ok=True)

    # Write the new flat list to the output file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(simplified_list, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Successfully created simplified JSON file at: {output_path}")
    return output_path
