# This script analyzes LDD data and generates a cleanup report
# Save this file and run it in an environment with the required data file

import json
from datetime import datetime, timedelta

with open("LDD data.txt", "r") as file:
    lines = file.readlines()

user_ldd_map = {}
for line in lines:
    parts = line.strip().split(",")
    if len(parts) >= 3:
        hostname = parts[0].strip()
        user = parts[1].strip()
        creation_date_str = parts[2].strip()
        user_ldd_map.setdefault(user, []).append((hostname, creation_date_str))

cutoff_date = datetime.now() - timedelta(weeks=2)
cleanup_candidates = []

for user, ldd_list in user_ldd_map.items():
    if len(ldd_list) > 1:
        creation_dates = []
        for hostname, date_str in ldd_list:
            try:
                creation_date = datetime.strptime(date_str, "%Y-%m-%d")
                creation_dates.append((hostname, creation_date))
            except (TypeError, ValueError):
                continue

        if creation_dates:
            newest_ldd = max(creation_dates, key=lambda x: x[1])
            if newest_ldd[1] < cutoff_date:
                cleanup_candidates.append({
                    "user": user,
                    "ldds": [hostname for hostname, _ in creation_dates],
                    "newest_ldd": newest_ldd[0],
                    "newest_ldd_date": newest_ldd[1].strftime("%Y-%m-%d")
                })

with open("ldd_cleanup_report.json", "w") as report_file:
    json.dump(cleanup_candidates, report_file, indent=4)

print(f"Detection complete. {len(cleanup_candidates)} users eligible for cleanup. Report saved to ldd_cleanup_report.json.")
