

import json
import os
import time
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
# 1. Set up your Google API Key
load_dotenv()  # This loads variables from .env into the environment

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    # Making the API key optional for cases where the module is imported without needing classification
    print("Warning: GOOGLE_API_KEY environment variable not set. Classification will not work.")
    genai_configured = False
else:
    genai.configure(api_key=API_KEY)
    genai_configured = True

# 2. Define the categories and instructions for the Gemini model
CATEGORIES = {
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


def generate_classification_prompt(batch_items):
    """Generates the prompt for the Gemini API call."""
    category_list_str = "\n".join([f"- **{cat}**: {desc}" for cat, desc in CATEGORIES.items()])
    items_to_classify_str = json.dumps(batch_items, indent=2, ensure_ascii=False)
    prompt = f'''
    You are an expert academic classifier specializing in statistics. Your task is to classify each research item into one of the following categories based on its title and abstract.

    **Categories and Descriptions:**
    {category_list_str}

    **Instructions:**
    1. Analyze the title and abstract for each item in the JSON array below.
    2. For each item, determine the most fitting category from the list provided.
    3. Your response MUST be a valid JSON object that maps each 'id' to its corresponding category name.
    4. The category name MUST be one of these exact strings: {", ".join(CATEGORIES.keys())}.
    5. Do NOT include any explanations, comments, or markdown formatting (like ```json) in your response.

    **Research Items to Classify:**
    {items_to_classify_str}

    **Required Output Format (JSON object):**
    {{
      "id_1": "CategoryName",
      "id_2": "CategoryName",
      ...
    }}
    '''
    return prompt


def classify_theses(input_filename, output_dir="output", batch_size=20):
    """Loads, classifies, and saves thesis data with improved robustness."""
    if not genai_configured:
        print("Error: Gemini API key not configured. Cannot proceed with classification.")
        return None

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found. Please run the scraper first.")
        return None

    model = genai.GenerativeModel('gemini-1.5-pro-latest')

    tasks = []
    task_id_counter = 0
    for year, theses in data.items():
        for title, details in theses.items():
            if "study_focus" in details:
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
        return input_filename # Return original file if no changes made

    print(f"Found {len(tasks)} items to classify. Starting process in batches of {batch_size}...")

    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        batch_input_for_prompt = [{"id": t["id"], "title": t["title"], "abstract": t["abstract"]} for t in batch]

        print(f"  - Processing batch {i//batch_size + 1}/{(len(tasks) + batch_size - 1)//batch_size}...")

        prompt = generate_classification_prompt(batch_input_for_prompt)

        classifications = {}
        retries = 3
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
            category = classifications.get(task_id)
            
            if category and category in CATEGORIES:
                task["original_object"]["study_focus"] = category
            else:
                task["original_object"]["study_focus"] = "Classification Failed"
                if category:
                    print(f"    - Warning: Invalid category '{category}' for {task_id}. Defaulting to failed.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(output_dir, f'unhas_repository_classified_{timestamp}.json')
    os.makedirs(output_dir, exist_ok=True)
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Classification complete! Results saved to '{output_filename}'.")
    return output_filename
