import json
import csv
from datetime import datetime
from collections import defaultdict
from email.mime.text import MIMEText
import smtplib

# Constants
INPUT_JSON = "ldd_vdi_data.json"
INPUT_CSV = "1000158532.jpg.csv"
OUTPUT_FILE = "ldd_cleanup_emails.txt"
SMTP_SERVER = "mailrelay.troweprice.com"
SMTP_PORT = 25
DAYS_LIMIT = 14  # Ignore LDDs used in the last 14 days

def send_email(user_email, user_name, hostname, last_login_date, home_dir):
    subject = f"[ACTION REQUIRED] LDD Cleanup for Host {hostname}"
    body = f"""Dear {user_name},

Our records indicate that you currently have multiple LDDs assigned to you, and the host "{hostname}" has not been accessed since {last_login_date}.

As part of our monthly LDD cleanup policy:
- Only one LDD is permitted unless there's a documented business requirement.
- LDDs unused for more than 14 days are subject to removal.

**Action Required:**
Please review the contents of the following home directory:  
{home_dir}

If this LDD is no longer needed, kindly raise a request to delete it via the ServiceNow LDD Decommission process. If needed for a valid business reason, please document the justification.

Thank you for your cooperation.

Regards,  
CDE Ops Team
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "no-reply@troweprice.com"
    msg["To"] = user_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.send_message(msg)
        print(f"[✅] Email sent to {user_email} for host {hostname}")
    except Exception as e:
        print(f"[❌] Failed to send email to {user_email}: {e}")

def should_notify(ldd):
    last_login_str = ldd.get("citrix_last_connection_date")
    if not last_login_str:
        return True
    try:
        last_login = datetime.strptime(last_login_str, "%Y-%m-%d")
        return (datetime.today() - last_login).days > DAYS_LIMIT
    except Exception:
        return True

def load_json(json_file):
    try:
        with open(json_file) as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load JSON: {e}")
        return {}

def load_csv_users(csv_file):
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

def get_user_email(vdi_entry):
    email = vdi_entry.get("vdi_owner_email")
    if email:
        return email
    name = vdi_entry.get("vdi_owner_name")
    if name:
        parts = name.strip().replace(",", "").split()
        if len(parts) >= 2:
            last = parts[0].lower()
            first = parts[1].lower()
            return f"{first}.{last}@troweprice.com"
    return None

def notify_json_users(data):
    user_map = defaultdict(list)
    for _, info in data.items():
        email = get_user_email(info)
        if email:
            user_map[email].append(info)

    for email, ldds in user_map.items():
        if len(ldds) <= 1:
            continue
        for ldd in ldds:
            if should_notify(ldd):
                send_email(
                    user_email=email,
                    user_name=ldd.get("vdi_owner_name", "User"),
                    hostname=ldd.get("hostname", "Unknown"),
                    last_login_date=ldd.get("citrix_last_connection_date", "Unknown"),
                    home_dir=ldd.get("home_directory", "Unknown")
                )

def write_emails_from_csv(csv_users, output_file):
    with open(output_file, "w") as f:
        for user, hostnames in csv_users.items():
            hosts = ", ".join(hostnames)
            email_body = f"""--- EMAIL TO: {user} ---
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
            print(f"[INFO] Writing email for {user}")
            f.write(email_body + "\n\n")
    print(f"[✅] All emails written to {output_file}")

# Entry
if __name__ == "__main__":
    print("[INFO] Starting LDD Cleanup Notifier...")

    json_data = load_json(INPUT_JSON)
    notify_json_users(json_data)

    csv_users = load_csv_users(INPUT_CSV)
    write_emails_from_csv(csv_users, OUTPUT_FILE)
