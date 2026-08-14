"""
GitHub Issues Assignee Auto-Scheduler.

Assigns GitHub issues to the respective team members based on issue roles:
- Viraj (Viraj281105): Orchestration & Infra
- Arya Chandak (aryachandak10): Frontend / UI
- Sanjali (sanjalipaygude1): Data curation, prompts, documentation
- Anurag Pawar (anuragpawars): QA, testing, visual OCR, and secondary UI
"""

import subprocess
import json
import time

REPO = "Viraj281105/Arogyarakshak"

ASSIGNEES = {
    "Viraj": "Viraj281105",
    "Arya": "aryachandak10",
    "Sanjali": "sanjalipaygude1",
    "Anurag": "anuragpawars"
}

def run_command(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    return result

def main():
    print("==> Fetching all issues from GitHub...")
    res = run_command(f'gh issue list --repo "{REPO}" --state all --limit 200 --json number,title,labels')
    
    if res.returncode != 0:
        print("Error fetching issues:", res.stderr.strip())
        return
        
    try:
        issues = json.loads(res.stdout)
        print(f"Loaded {len(issues)} issues.")
    except Exception as e:
        print("Failed to parse issues JSON:", e)
        return

    print("==> Assigning issues based on roles...")
    for issue in issues:
        number = issue["number"]
        title = issue["title"]
        labels = [l["name"] for l in issue["labels"]]
        
        assignee = None
        
        # 1. Viraj: Orchestration & Infra
        if any(l in labels for l in ["role:orchestration", "role:infra"]):
            assignee = ASSIGNEES["Viraj"]
            
        # 2. QA/OCR and secondary UI (Anurag)
        elif "role:ocr-data" in labels:
            assignee = ASSIGNEES["Anurag"]
            
        # 3. Frontend UI (Split between Arya and Anurag)
        elif "role:frontend" in labels:
            # Let Anurag handle advanced visualization / interactive widgets as secondary UI
            if any(kw in title.lower() for kw in ["conversational", "anomalies", "encryption", "tracing"]):
                assignee = ASSIGNEES["Anurag"]
            else:
                assignee = ASSIGNEES["Arya"]
                
        # 4. Data curation & QA (Split between Sanjali and Anurag)
        elif "role:data-qa" in labels:
            # If it's a test/evaluation metrics task -> Anurag (QA)
            if any(kw in title.lower() for kw in ["eval", "accuracy", "precision", "wer", "cer", "latency"]):
                assignee = ASSIGNEES["Anurag"]
            else:
                assignee = ASSIGNEES["Sanjali"]
                
        if assignee:
            print(f"Assigning Issue #{number} ('{title}') -> {assignee}...")
            cmd = f'gh issue edit {number} --repo "{REPO}" --add-assignee "{assignee}"'
            edit_res = run_command(cmd)
            if edit_res.returncode == 0:
                print(f"  Successfully assigned.")
            else:
                stderr = edit_res.stderr.strip()
                if "is not a collaborator" in stderr:
                    print(f"  [WARNING] Could not assign: {assignee} has not accepted the repository invitation yet.")
                else:
                    print(f"  Failed: {stderr}")
            # Prevent rate limit throttling
            time.sleep(0.3)
        else:
            print(f"Skipping Issue #{number} ('{title}') - no role assignment matched.")

    print("==> Issue assignment completed.")

if __name__ == "__main__":
    main()
