import json
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from email.mime.text import MIMEText

# ==== Constants ====
INPUT_JSON = "ldd_vdi_data.json"
INPUT_CSV = "1000158532.jpg.csv"
OUTPUT_EMAIL_FILE = "ldd_cleanup_emails.txt"
DAYS_LIMIT = 14  # Ignore new LDDs created within the past 14 days

# ==== MOCK Email Sender ====
def send_email(user_email, user_name, hostname, last_login_date, home_dir):
    subject = f"[ACTION REQUIRED] LDD Cleanup for Host {hostname}"
    body = f"""Dear {user_name},

Our records indicate that you currently have multiple LDDs assigned to you, and the host "{hostname}" has not been accessed since {last_login_date}.

As part of our monthly LDD cleanup policy:
- Only one LDD is permitted unless there's a documented business requirement.
- LDDs unused for more than {DAYS_LIMIT} days are subject to removal.

**Action Required:**
Please review the contents of the following home directory:  
{home_dir}

If this LDD is no longer needed, kindly raise a request to delete it via the ServiceNow LDD Decommission process. If needed for a valid business reason, please document the justification.

Thank you for your cooperation.

Regards,  
CDE Ops Team
"""
    print(f"\n[MOCK EMAIL]")
    print(f"To: {user_email}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    print(f"[✅] Simulated sending email to {user_email} for host {hostname}\n")

# ==== Check whether to notify based on last login ====
def should_notify(ldd):
    last_login_str = ldd.get("citrix_last_connection_date")
    if not last_login_str:
        return True
    try:
        last_login = datetime.strptime(last_login_str, "%Y-%m-%d")
        return (datetime.today() - last_login).days > DAYS_LIMIT
    except Exception:
        return True

# ==== Load JSON Data ====
def load_json(json_file):
    with open(json_file) as f:
        return json.load(f)

# ==== Notify Users from JSON (mock emails) ====
def notify_users_from_json(data):
    print("[INFO] Processing JSON-based LDD data...")
    user_map = defaultdict(list)
    for hostname, info in data.items():
        email = info.get("vdi_owner_email")
        if not email:
            continue
        user_map[email].append(info)

    for email, ldds in user_map.items():
        if len(ldds) <= 1:
            continue  # Only notify if user has more than 1 LDD

        for ldd in ldds:
            if should_notify(ldd):
                send_email(
                    user_email=ldd.get("vdi_owner_email"),
                    user_name=ldd.get("vdi_owner_name", "User"),
                    hostname=ldd.get("hostname", "Unknown"),
                    last_login_date=ldd.get("citrix_last_connection_date", "Unknown"),
                    home_dir=ldd.get("home_directory", "Unknown")
                )

# ==== Load CSV Data ====
def load_ldd_users_from_csv(csv_file):
    users = {}
    try:
        with open(csv_file, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user = row.get("User", "").strip()
                hostnames_raw = row.get("Hostname List", "")
                hostnames = [h.strip() for h in hostnames_raw.split(",") if h.strip()]
                if user and len(hostnames) > 1:
                    users[user] = hostnames
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
    print(f"[INFO] Loaded {len(users)} users with multiple LDDs from CSV.")
    return users

# ==== Generate Email Text from CSV ====
def generate_email(user, hostnames):
    hosts = ", ".join(hostnames)
    return f"""--- EMAIL TO: {user} ---
Subject: LDD Cleanup Action Required

Dear {user},

Our monthly audit shows you currently have multiple Linux Developer Desktops (LDDs) assigned:
→ Hostnames: {hosts}

As part of general housekeeping, users are allowed only one LDD by default. 
Please review your LDD usage and remove any that are not required.

If there is a justified requirement, please inform the support team.

Otherwise, kindly raise a request to delete the extra LDDs and clean up any unnecessary files from your NFS home directory.

Thank you for your cooperation.

Regards,  
InfraOps Team
"""

# ==== Save All CSV Emails to File ====
def evaluate_and_email_csv(users_dict, output_file):
    with open(output_file, "w") as f:
        for user, hostnames in users_dict.items():
            print(f"[INFO] Generating email for user: {user}")
            email_text = generate_email(user, hostnames)
            print(email_text)
            f.write(email_text + "\n\n")
    print(f"\n✅ Email messages saved to: {output_file}")

# ==== MAIN ====
if __name__ == "__main__":
    print("[INFO] Starting LDD Cleanup Notifier...")

    # 1. Process JSON-based LDDs
    try:
        data = load_json(INPUT_JSON)
        print(f"[INFO] Loaded {len(data)} LDD entries from JSON.")
        notify_users_from_json(data)
    except Exception as e:
        print(f"[ERROR] Failed to process JSON: {e}")

    # 2. Process CSV-based LDDs
    try:
        ldd_users = load_ldd_users_from_csv(INPUT_CSV)
        evaluate_and_email_csv(ldd_users, OUTPUT_EMAIL_FILE)
    except Exception as e:
        print(f"[ERROR] Failed to process CSV: {e}")
