import json
import os
import time
from datetime import datetime

import google.generativeai as genai

from ..config.settings import Config


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


def get_categories_for_major(config: Config) -> dict:
    """Get classification categories for the specified major."""
    major_categories = config.classification_categories.get(
        config.target_major,
        config.classification_categories.get("default", {})
    )
    return major_categories


def generate_classification_prompt(batch_items, categories: dict):
    """Generates the prompt for the Gemini API call with support for secondary focus."""
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


def validate_classification_config(config: Config, force_default_categories: bool = False) -> bool:
    """
    Validate classification configuration.
    
    Args:
        config: Configuration object to validate.
        
    Returns:
        bool: True if validation passes, False if blocked due to default categories
        
    Raises:
        ValueError: If configuration is invalid (missing API key, etc.).
    """
    if not config.google_api_key:
        raise ValueError(
            "Google API key not configured. Please set GOOGLE_API_KEY environment "
            "variable or add it to your configuration file."
        )
    
    major_categories = get_categories_for_major(config)
    if not major_categories:
        raise ValueError(
            f"No classification categories defined for major '{config.target_major}'"
        )
    
    for category, description in major_categories.items():
        if not description.strip():
            raise ValueError(f"Empty description for category: {category}")
    
    # CRITICAL: Check if user has confirmed they've customized categories
    if not config.user_defined_categories and not force_default_categories:
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
        
        # Return False to indicate classification was blocked
        return False
    elif not config.user_defined_categories and force_default_categories:
        from rich.console import Console
        console = Console()
        console.print("\n[yellow]⚠️  Using default categories for testing (accuracy may be lower)[/yellow]")
    
    # If we reach here, validation passed
    return True


def classify_theses(input_filename: str, output_dir: str = "output", 
                   config: Config = None, batch_size: int = None, force_default_categories: bool = False) -> str:
    """Loads, classifies, and saves thesis data with improved robustness and secondary focus support."""
    
    # Use legacy behavior if config not provided
    if config is None:
        print("Warning: Using legacy configuration mode. Consider updating to use Config object.")
        # Try to get API key from environment
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Error: Gemini API key not configured. Cannot proceed with classification.")
            return None
        genai.configure(api_key=api_key)
        categories = {
            "Regresi": "Fokus pada **inferensi statistik** untuk memahami dan mengukur hubungan antar variabel menggunakan model dengan **bentuk fungsional yang telah ditentukan** (misalnya, linear, logistik). Tujuan utamanya adalah menjelaskan *seberapa besar* pengaruh satu variabel terhadap variabel lain.",
            "Regresi Nonparametrik": "Fokus pada pemodelan hubungan antar variabel **TANPA asumsi bentuk fungsional tertentu**. Metode ini sangat fleksibel dan digunakan ketika pola data kompleks, non-linear, dan tidak diketahui sebelumnya. Tujuannya adalah membiarkan data 'berbicara' untuk membentuk modelnya sendiri.",
            "Pengendalian Kualitas Statistika": "Fokus pada **pemantauan (monitoring) proses yang sedang berjalan** untuk memastikan stabilitas dan konsistensi output. Alat utamanya adalah **peta kendali (control chart)** untuk mendeteksi variasi yang tidak wajar secara visual dan menjaga proses tetap dalam spesifikasi.",
            "Perancangan Percobaan": "Fokus pada **perancangan eksperimen secara proaktif SEBELUM data dikumpulkan**. Tujuannya adalah untuk secara efisien membandingkan efek dari berbagai **perlakuan (treatments)** melalui intervensi aktif untuk menemukan pengaturan atau kondisi yang paling optimal.",
            "Analisis Runtun Waktu": "Analisis data yang variabel utamanya adalah **waktu**. Metode ini secara khusus menangani data dengan **ketergantungan temporal** (nilai saat ini dipengaruhi oleh nilai sebelumnya). Tujuan utamanya adalah memahami pola historis dan melakukan **peramalan (forecasting)**.",
            "Machine Learning": "Fokus utama pada **akurasi prediksi**. Tujuannya adalah membangun algoritma yang dapat belajar dari data untuk membuat prediksi atau klasifikasi seakurat mungkin, seringkali **mengorbankan interpretasi model** demi performa prediktif yang superior.",
            "Analisis Data Spasial": "Analisis data yang variabel utamanya adalah **lokasi geografis**. Metode ini secara khusus menangani data dengan **ketergantungan spasial** (nilai di satu lokasi dipengaruhi oleh nilai di lokasi tetangganya). Fokus utamanya adalah pemetaan dan pemodelan **autokorelasi spasial**.",
            "Analisis Survival": "Metode statistik khusus untuk menganalisis data **'waktu-ke-kejadian' (time-to-event)**. Fokusnya adalah memodelkan waktu hingga suatu peristiwa terjadi dan menangani **data tersensor (censored data)**, di mana peristiwa tersebut tidak diamati untuk semua subjek.",
            "Ekonometrika dan Manajemen Risiko": "Aplikasi statistik khusus pada **data keuangan dan ekonomi** untuk mengukur dan mengelola risiko. Fokus utamanya adalah kuantifikasi risiko investasi melalui metrik seperti **Value at Risk (VaR) dan CVaR**, pemodelan portofolio, dan analisis dependensi aset.",
            "Lainnya": "Kategori untuk metodologi statistik yang tidak memiliki karakteristik unik dari kategori lain yang telah disebutkan. Contohnya meliputi **psikometri, bioinformatika, atau analisis data kategorik murni**."
        }
        actual_batch_size = batch_size or 20
        retries = 3
    else:
        # Use new configuration system
        if not validate_classification_config(config, force_default_categories):
            # Classification was blocked due to default categories
            return None
            
        genai.configure(api_key=config.google_api_key)
        categories = get_categories_for_major(config)
        actual_batch_size = batch_size or config.batch_size
        retries = config.classification_retries

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found. Please run the scraper first.")
        return None

    model = genai.GenerativeModel('gemini-2.5-pro')

    tasks = []
    task_id_counter = 0
    for year, theses in data.items():
        for title, details in theses.items():
            # Check if already classified (backward compatibility with old format)
            if "study_focus" in details:
                if isinstance(details["study_focus"], dict) and "primary" in details["study_focus"]:
                    continue  # Already has new format
                elif isinstance(details["study_focus"], str):
                    # Convert old format to new format
                    old_focus = details["study_focus"]
                    if old_focus != "Classification Failed":
                        details["study_focus"] = {
                            "primary": old_focus,
                            "secondary": old_focus  # Default secondary to same as primary
                        }
                    continue

            abstract = details.get("abstract", "") or ""
            if "LIHAT DI FULL TEXT" in abstract.upper():
                abstract = ""

            tasks.append({
                "id": f"task_{task_id_counter}",
                "title": title,
                "abstract": abstract,
                "original_object": details
            })
            task_id_counter += 1

    if not tasks:
        print("✅ All items are already classified. No action needed.")
        return input_filename

    print(f"Found {len(tasks)} items to classify. Starting process in batches of {actual_batch_size}...")

    for i in range(0, len(tasks), actual_batch_size):
        batch = tasks[i:i + actual_batch_size]
        batch_input_for_prompt = [{"id": t["id"], "title": t["title"], "abstract": t["abstract"]} for t in batch]

        print(f"  - Processing batch {i//actual_batch_size + 1}/{(len(tasks) + actual_batch_size - 1)//actual_batch_size}...")

        prompt = generate_classification_prompt(batch_input_for_prompt, categories)

        classifications = {}
        for attempt in range(retries):
            try:
                response = model.generate_content(prompt)
                
                if not response.text:
                    raise ValueError("API returned an empty response.")

                cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
                
                classifications = json.loads(cleaned_text)
                print("    - Batch successfully processed by API.")
                break
            except (json.JSONDecodeError, ValueError) as e:
                print(f"    - Warning: API call or parsing failed on attempt {attempt + 1}. Error: {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    print(f"    - Problematic API response text: '{response.text}'")
                if attempt < retries - 1:
                    time.sleep(5)
                else:
                    print(f"    - Error: Batch failed after {retries} attempts. Items will be marked 'Classification Failed'.")
            except Exception as e:
                print(f"    - Warning: An unexpected error occurred on attempt {attempt + 1}. Error: {e}")
                if attempt < retries - 1:
                    time.sleep(5)
                else:
                    print(f"    - Error: Batch failed after {retries} attempts. Items will be marked 'Classification Failed'.")

        for task in batch:
            task_id = task["id"]
            classification = classifications.get(task_id)
            
            if classification and isinstance(classification, dict):
                primary = classification.get("primary")
                secondary = classification.get("secondary")
                
                if primary in categories and secondary in categories:
                    task["original_object"]["study_focus"] = {
                        "primary": primary,
                        "secondary": secondary
                    }
                else:
                    task["original_object"]["study_focus"] = "Classification Failed"
                    print(f"    - Warning: Invalid categories for {task_id}. Primary: '{primary}', Secondary: '{secondary}'")
            else:
                task["original_object"]["study_focus"] = "Classification Failed"
                if classification:
                    print(f"    - Warning: Invalid classification format for {task_id}: {classification}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract faculty and major from input filename, fallback to config if not found
    extracted_faculty, extracted_major = extract_faculty_major_from_filename(input_filename)
    
    if extracted_faculty and extracted_major:
        filename_suffix = f"{extracted_faculty}_{extracted_major}_classified_{timestamp}"
    elif config and hasattr(config, 'target_faculty') and hasattr(config, 'target_major') and config.target_faculty and config.target_major:
        filename_suffix = f"{config.target_faculty}_{config.target_major}_classified_{timestamp}"
    else:
        filename_suffix = f"unhas_repository_classified_{timestamp}"
    output_filename = os.path.join(output_dir, f'{filename_suffix}.json')
    os.makedirs(output_dir, exist_ok=True)
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Classification complete! Results saved to '{output_filename}'.")
    return output_filename
