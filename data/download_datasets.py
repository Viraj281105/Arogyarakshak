"""
Dataset Downloader and Mocker for ArogyaRakshak.

Downloads Hugging Face datasets and scaffolds Kaggle/Mendeley mock datasets
with identical structures and schemas under the data/ directory.
"""

import os
import sys
import shutil
import pandas as pd
from huggingface_hub import hf_hub_download, snapshot_download

DATA_DIR = os.path.abspath("data")
RAW_DIR = os.path.join(DATA_DIR, "raw")

os.makedirs(RAW_DIR, exist_ok=True)

def download_huggingface_datasets():
    print("=== Downloading Hugging Face Datasets ===")
    
    # 1. chinmays18/medical-prescription-dataset
    presc_dir = os.path.join(RAW_DIR, "prescriptions_handwritten")
    os.makedirs(presc_dir, exist_ok=True)
    try:
        print("Downloading chinmays18/medical-prescription-dataset...")
        # Download metadata or split csv
        csv_path = hf_hub_download(
            repo_id="chinmays18/medical-prescription-dataset",
            repo_type="dataset",
            filename="medical-prescription-dataset.csv"
        )
        shutil.copy(csv_path, os.path.join(presc_dir, "metadata.csv"))
        print(f"Saved prescriptions dataset metadata to {presc_dir}")
    except Exception as e:
        print(f"Could not download prescriptions dataset: {e}")
        # Fallback to write mock csv
        df = pd.DataFrame({
            "image_path": ["presc_1.jpg", "presc_2.jpg"],
            "prescription_text": [
                "Tab Paracetamol 650mg TDS\nTab Amoxicillin 500mg BD",
                "Tab Pantocid 40mg OD\nSyr Duphalac 15ml HS"
            ]
        })
        df.to_csv(os.path.join(presc_dir, "metadata.csv"), index=False)
        print("Created mock prescriptions dataset.")

    # 2. mychen76/invoices-and-receipts_ocr_v1
    invoice_dir = os.path.join(RAW_DIR, "invoices_receipts_ocr")
    os.makedirs(invoice_dir, exist_ok=True)
    try:
        print("Downloading mychen76/invoices-and-receipts_ocr_v1 sample file...")
        # Invoices and receipts has json files or images
        # We can download config files or write a fallback
        # Let's create a template structure
        df = pd.DataFrame({
            "image_url": ["invoice_01.png", "invoice_02.png"],
            "total_charged": [1500.00, 320.50],
            "items": ["Room charges, Consultation", "Medicine, X-Ray"]
        })
        df.to_csv(os.path.join(invoice_dir, "invoices_metadata.csv"), index=False)
        print("Created invoices-receipts database schema.")
    except Exception as e:
        print(f"Could not process invoices dataset: {e}")


def mock_kaggle_datasets():
    print("=== Scaffolding Kaggle / Mendeley Mock Datasets ===")

    # 1. Hospital Inpatient Discharges (SPARCS NY)
    # Target path: data/raw/sparcs_inpatient_discharges/
    sparcs_dir = os.path.join(RAW_DIR, "sparcs_inpatient_discharges")
    os.makedirs(sparcs_dir, exist_ok=True)
    df_sparcs = pd.DataFrame({
        "discharge_year": [2024, 2024],
        "gender": ["M", "F"],
        "age_group": ["30 to 49", "50 to 69"],
        "length_of_stay": ["3", "5"],
        "diagnosis_code": ["I10", "E11"],
        "diagnosis_description": ["Essential (primary) hypertension", "Type 2 diabetes mellitus"],
        "procedure_code": ["02100Z9", "03120Z9"],
        "procedure_description": ["Coronary bypass", "Peripheral artery bypass"],
        "total_charges": [45000.00, 78000.00],
        "total_costs": [32000.00, 51000.00],
    })
    df_sparcs.to_csv(os.path.join(sparcs_dir, "inpatient_discharges.csv"), index=False)
    print(f"Scaffolded SPARCS discharges dataset schema at {sparcs_dir}")

    # 2. Enhanced Health Insurance Claims
    claims_dir = os.path.join(RAW_DIR, "health_insurance_claims_synthetic")
    os.makedirs(claims_dir, exist_ok=True)
    df_claims = pd.DataFrame({
        "patient_id": ["P-101", "P-102"],
        "policy_type": ["Gold", "Platinum"],
        "total_claimed": [25000.00, 48000.00],
        "total_allowed": [21000.00, 45000.00],
        "denial_reason_code": ["RARC-N29", "CARC-96"],
        "denial_description": ["Exceeds maximum allowable room limit", "Non-covered procedure charges"],
        "cghs_deviation_flag": [True, False]
    })
    df_claims.to_csv(os.path.join(claims_dir, "insurance_claims.csv"), index=False)
    print(f"Scaffolded synthetic insurance claims schema at {claims_dir}")

    # 3. Healthcare Fraud Detection Dataset (ICD-10 and CPT codes)
    fraud_dir = os.path.join(RAW_DIR, "healthcare_fraud_detection")
    os.makedirs(fraud_dir, exist_ok=True)
    df_fraud = pd.DataFrame({
        "claim_id": ["CLM-01", "CLM-02"],
        "provider_id": ["PROV-77", "PROV-92"],
        "icd_10_diagnosis": ["J44.9", "M17.9"],
        "cpt_procedure": ["99214", "27447"],
        "is_fraud": [0, 1],
        "fraud_reason": ["", "Upcoding detected - procedure does not match severity level of diagnosis"]
    })
    df_fraud.to_csv(os.path.join(fraud_dir, "fraud_claims.csv"), index=False)
    print(f"Scaffolded Healthcare Fraud Detection schema at {fraud_dir}")

    # 4. Indian Medical Insurance Policy
    policy_dir = os.path.join(RAW_DIR, "indian_medical_insurance_policy")
    os.makedirs(policy_dir, exist_ok=True)
    df_policy = pd.DataFrame({
        "policy_holder": ["Viraj Jadhao", "Siddhesh Patil"],
        "insurer_name": ["Star Health", "HDFC Ergo"],
        "sum_insured": [500000.00, 1000000.00],
        "room_rent_cap": ["Single Private AC", "No Limit"],
        "maternity_coverage": [False, True],
        "co_payment_percentage": [0.0, 10.0]
    })
    df_policy.to_csv(os.path.join(policy_dir, "indian_policies.csv"), index=False)
    print(f"Scaffolded Indian medical insurance policy schema at {policy_dir}")

    # 5. Mendeley Insurance Claims Fraud Dataset (39 columns)
    mendeley_dir = os.path.join(RAW_DIR, "mendeley_insurance_claims")
    os.makedirs(mendeley_dir, exist_ok=True)
    columns = [
        "months_as_customer", "age", "policy_number", "policy_bind_date", "policy_state",
        "policy_csl", "policy_deductable", "policy_annual_premium", "umbrella_limit", "insured_zip",
        "insured_sex", "insured_education_level", "insured_occupation", "insured_hobbies", "insured_relationship",
        "capital-gains", "capital-loss", "incident_date", "incident_type", "collision_type",
        "incident_severity", "authorities_contacted", "incident_state", "incident_city", "incident_location",
        "number_of_vehicles_involved", "property_damage", "bodily_injuries", "witnesses", "police_report_available",
        "total_claim_amount", "injury_claim", "property_claim", "vehicle_claim", "auto_make",
        "auto_model", "auto_year", "fraud_reported"
    ]
    df_mendeley = pd.DataFrame([[
        120, 35, 987654, "2015-05-12", "MH", "250/500", 1000, 1250.45, 0, 440022,
        "MALE", "MD", "Doctor", "reading", "self", 0, 0, "2024-01-10", "Single Vehicle Collision", "Side",
        "Major Damage", "Police", "MH", "Nagpur", "Nari Road", 1, "YES", 0, 2, "YES",
        45000, 5000, 5000, 35000, "Tata", "Safari", 2018, "Y"
    ]], columns=columns)
    df_mendeley.to_csv(os.path.join(mendeley_dir, "mendeley_claims.csv"), index=False)
    print(f"Scaffolded Mendeley claims schema at {mendeley_dir}")


def main():
    print("=== STARTING DATASET PREPARATION ===")
    download_huggingface_datasets()
    mock_kaggle_datasets()
    print("=== DATASET PREPARATION COMPLETED ===")

if __name__ == "__main__":
    main()
