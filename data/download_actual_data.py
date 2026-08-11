"""
Actual Dataset Downloader for ArogyaRakshak.

Downloads actual prescription images and annotations from Hugging Face,
actual invoices OCR parquet files, and direct PDF downloads for CGHS rates
and insurance company registries.
"""

import os
import shutil
import urllib.request
import requests
import pandas as pd
from huggingface_hub import hf_hub_download

RAW_DIR = os.path.abspath("data/raw")
os.makedirs(RAW_DIR, exist_ok=True)

# 1. Download Actual Prescription Samples from Hugging Face
def download_prescriptions():
    print("=== Downloading Actual Prescription Images and Annotations ===")
    presc_dir = os.path.join(RAW_DIR, "prescriptions_handwritten")
    os.makedirs(presc_dir, exist_ok=True)
    
    samples = [
        "prescription_00006",
        "prescription_00025",
        "prescription_00027",
        "prescription_00030",
        "prescription_00032"
    ]
    
    for sample in samples:
        try:
            print(f"Downloading {sample} png and json from Hugging Face...")
            img_path = hf_hub_download(
                repo_id="chinmays18/medical-prescription-dataset",
                repo_type="dataset",
                filename=f"test/images/{sample}.png"
            )
            json_path = hf_hub_download(
                repo_id="chinmays18/medical-prescription-dataset",
                repo_type="dataset",
                filename=f"test/annotations/{sample}.json"
            )
            shutil.copy(img_path, os.path.join(presc_dir, f"{sample}.png"))
            shutil.copy(json_path, os.path.join(presc_dir, f"{sample}.json"))
            print(f"Successfully saved {sample} to {presc_dir}")
        except Exception as e:
            print(f"Error downloading {sample}: {e}")

# 2. Download and Parse Actual Invoices OCR Parquet from Hugging Face
def download_invoices():
    print("\n=== Downloading and Parsing Actual Invoices OCR Data ===")
    invoice_dir = os.path.join(RAW_DIR, "invoices_receipts_ocr")
    os.makedirs(invoice_dir, exist_ok=True)
    
    try:
        parquet_path = hf_hub_download(
            repo_id="mychen76/invoices-and-receipts_ocr_v1",
            repo_type="dataset",
            filename="data/test-00000-of-00001-af2d92d1cee28514.parquet"
        )
        print("Reading Parquet file...")
        df = pd.read_parquet(parquet_path)
        # Extract a subset of rows with clean textual content
        df_subset = df.head(50)
        df_subset.to_csv(os.path.join(invoice_dir, "invoices_metadata.csv"), index=False)
        print(f"Saved {len(df_subset)} actual invoice records to {invoice_dir}")
    except Exception as e:
        print(f"Error downloading/parsing invoices: {e}")

# 3. Download CGHS Rates Static PDF Mirror
def download_cghs_rates():
    print("\n=== Downloading CGHS Rates Static PDF ===")
    cghs_url = "https://www.csir.res.in/sites/default/files/2025-10/cghs_rates.pdf"
    target_path = os.path.join(RAW_DIR, "cghs_rates.pdf")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        print(f"Fetching from {cghs_url}...")
        response = requests.get(cghs_url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            with open(target_path, "wb") as f:
                f.write(response.content)
            print(f"Saved CGHS Rates PDF to {target_path}")
        else:
            print(f"Failed to download CGHS rates. HTTP Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading CGHS Rates: {e}")

# 4. Download Insurance Companies PDF Register
def download_insurance_companies():
    print("\n=== Downloading Insurance Companies Registry PDF ===")
    testbook_url = "https://cdn.testbook.com/1695817356599-insurance-companies.pdf/1695817359.pdf"
    target_path = os.path.join(RAW_DIR, "insurance_companies.pdf")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        print(f"Fetching from {testbook_url}...")
        response = requests.get(testbook_url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            with open(target_path, "wb") as f:
                f.write(response.content)
            print(f"Saved Insurance Companies PDF to {target_path}")
        else:
            print(f"Failed to download insurance register. HTTP Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading Insurance register: {e}")

def main():
    print("=== STARTING ACTUAL DATASET DOWNLOADS ===")
    download_prescriptions()
    download_invoices()
    download_cghs_rates()
    download_insurance_companies()
    print("=== ACTUAL DATASET DOWNLOADS COMPLETED ===")

if __name__ == "__main__":
    main()
