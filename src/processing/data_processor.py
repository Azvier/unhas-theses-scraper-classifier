
import json
import os
import re
from datetime import datetime
import pandas as pd

from ..config.settings import Config


def sanitize_xml_text(text):
    """
    Sanitize text to remove characters that are illegal in XML/Excel.
    
    This function replaces Unicode characters that can cause XML parsing errors
    when creating Excel files. XML 1.0 specification allows only:
    - #x9 (tab), #xA (LF), #xD (CR)  
    - #x20-#xD7FF (excluding #xD800-#xDFFF surrogate pairs)
    - #xE000-#xFFFD (excluding #xFFFE-#xFFFF)
    - #x10000-#x10FFFF
    """
    if not isinstance(text, str):
        return text
    
    # Dictionary of problematic characters and their replacements
    replacements = {
        # Smart quotes
        '"': '"',  # Left double quotation mark  
        '"': '"',  # Right double quotation mark  
        ''': "'",  # Left single quotation mark
        ''': "'",  # Right single quotation mark
        
        # Dashes
        '—': '-',  # Em dash
        '–': '-',  # En dash
        
        # Superscript numbers
        '⁰': '0',
        '¹': '1', 
        '²': '2',
        '³': '3',
        '⁴': '4',
        '⁵': '5',
        '⁶': '6',
        '⁷': '7',
        '⁸': '8',
        '⁹': '9',
        '⁻': '-',  # Superscript minus
        
        # Subscript numbers
        '₀': '0',
        '₁': '1',
        '₂': '2', 
        '₃': '3',
        '₄': '4',
        '₅': '5',
        '₆': '6',
        '₇': '7',
        '₈': '8',
        '₉': '9',
        
        # Mathematical symbols
        '×': 'x',  # Multiplication sign
        '±': '+/-',  # Plus-minus sign
        '≤': '<=',  # Less than or equal to
        '≥': '>=',  # Greater than or equal to
        
        # Greek letters (common in scientific texts)
        'α': 'alpha',
        'β': 'beta', 
        'γ': 'gamma',
        'δ': 'delta',
        'λ': 'lambda',
        'μ': 'mu',
        'µ': 'mu',  # Micro sign
        'π': 'pi',
        'σ': 'sigma',
        'Ω': 'Omega',  # Greek Omega (also covers Ohm sign which has same appearance)
        
        # Degree and temperature symbols
        '°': ' deg',  # Degree sign
        '℃': 'C',    # Celsius
        '℉': 'F',    # Fahrenheit
        '˚': ' deg',  # Ring above (degree)
        
        # Other problematic characters
        '…': '...',  # Horizontal ellipsis
    }
    
    # Apply replacements
    sanitized_text = text
    for old_char, new_char in replacements.items():
        sanitized_text = sanitized_text.replace(old_char, new_char)
    
    # Remove XML-illegal control characters (keep tab, LF, CR)
    # XML 1.0 illegal: #x0-#x8, #xB, #xC, #xE-#x1F, #xFFFE, #xFFFF
    sanitized_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\uFFFE\uFFFF]', '', sanitized_text)
    
    # Remove surrogate pairs (invalid in XML)
    sanitized_text = re.sub(r'[\uD800-\uDFFF]', '', sanitized_text)
    
    return sanitized_text
def extract_faculty_major_from_filename(input_path: str) -> tuple:
    """
    Extract faculty and major names from the input filename.
    Expected format: faculty_major_timestamp.json or faculty_major_classified_timestamp.json
    
    Returns:
        tuple: (faculty, major) or (None, None) if extraction fails
    """
    try:
        # Get just the filename without path and extension
        filename = os.path.basename(input_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Split by underscore
        parts = filename_without_ext.split('_')
        
        if len(parts) >= 3:
            # Handle different filename patterns
            if 'classified' in parts:
                # Format: faculty_major_classified_timestamp
                faculty_idx = 0
                major_idx = 1
            elif 'simplified' in parts:
                # Format: faculty_major_simplified_timestamp  
                faculty_idx = 0
                major_idx = 1
            else:
                # Format: faculty_major_timestamp
                faculty_idx = 0
                major_idx = 1
            
            if len(parts) > major_idx:
                faculty = parts[faculty_idx]
                major = parts[major_idx]
                return faculty, major
                
    except Exception as e:
        print(f"Warning: Could not extract faculty/major from filename '{input_path}': {e}")
    
    return None, None


def convert_json_to_excel(input_path: str, output_dir: str = "output", config: Config = None) -> str:
    """Converts a classified JSON file to an Excel file with support for secondary focus."""
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
            
            # Handle study_focus - both old and new format
            study_focus = details.get('study_focus')
            if isinstance(study_focus, dict):
                # New format with primary/secondary
                row['primary_focus'] = study_focus.get('primary', 'Not Available')
                row['secondary_focus'] = study_focus.get('secondary', 'Not Available')
                row['study_focus'] = study_focus.get('primary', 'Not Available')  # For backward compatibility
            elif isinstance(study_focus, str):
                # Old format or failed classification
                row['primary_focus'] = study_focus
                row['secondary_focus'] = study_focus if study_focus != "Classification Failed" else "Not Available"
                row['study_focus'] = study_focus  # For backward compatibility
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
    preferred_columns = ['year', 'title', 'author', 'primary_focus', 'secondary_focus', 
                        'study_focus', 'abstract', 'item_type', 'date_deposited', 
                        'last_modified', 'url']
    
    # Reorder columns, keeping any additional columns at the end
    existing_columns = df.columns.tolist()
    ordered_columns = [col for col in preferred_columns if col in existing_columns]
    remaining_columns = [col for col in existing_columns if col not in preferred_columns]
    final_columns = ordered_columns + remaining_columns
    
    df = df[final_columns]
    
    # Sanitize all text columns to prevent XML parsing errors in Excel
    for col in df.columns:
        if df[col].dtype == 'object':  # String columns
            df[col] = df[col].apply(sanitize_xml_text)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract faculty and major from input filename, fallback to config if not found
    extracted_faculty, extracted_major = extract_faculty_major_from_filename(input_path)
    
    if extracted_faculty and extracted_major:
        filename_suffix = f"{extracted_faculty}_{extracted_major}_classified_{timestamp}"
    elif config and hasattr(config, 'target_faculty') and hasattr(config, 'target_major') and config.target_faculty and config.target_major:
        filename_suffix = f"{config.target_faculty}_{config.target_major}_classified_{timestamp}"
    else:
        filename_suffix = f"unhas_repository_classified_{timestamp}"
    output_filename = os.path.join(output_dir, f'{filename_suffix}.xlsx')
    os.makedirs(output_dir, exist_ok=True)
    df.to_excel(output_filename, index=False)
    print(f"✅ Data exported to '{output_filename}'")
    return output_filename


def simplify_repository_data(input_path: str, output_dir: str = "output", config: Config = None) -> str:
    """
    Reads a nested JSON repository file, flattens it, and extracts
    only the title, abstract, and study focus for each entry.
    Now supports both primary and secondary focus.
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract faculty and major from input filename, fallback to config if not found
    extracted_faculty, extracted_major = extract_faculty_major_from_filename(input_path)
    
    if extracted_faculty and extracted_major:
        filename_suffix = f"{extracted_faculty}_{extracted_major}_simplified_{timestamp}"
    elif config and hasattr(config, 'target_faculty') and hasattr(config, 'target_major') and config.target_faculty and config.target_major:
        filename_suffix = f"{config.target_faculty}_{config.target_major}_simplified_{timestamp}"
    else:
        filename_suffix = f"unhas_repository_simplified_{timestamp}"
    output_filename = f'{filename_suffix}.json'
    output_path = os.path.join(output_dir, output_filename)
    os.makedirs(output_dir, exist_ok=True)

    # Write the new flat list to the output file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(simplified_list, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Successfully created simplified JSON file at: {output_path}")
    return output_path