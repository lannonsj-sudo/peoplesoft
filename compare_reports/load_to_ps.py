"""
load_to_ps.py
Reads fiu_customizations.csv and loads it into the Oracle table
PS_FIU_CUSTOMIZ so the FIU_RETROFIT App Engine can process it.

Requirements:
    pip install cx_Oracle

Usage:
    python load_to_ps.py --dsn <tns_alias> --user <schema> --password <pwd>

Example:
    python load_to_ps.py --dsn HRPRD90 --user SYSADM --password sysadm
"""

import argparse
import csv
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Load FIU customizations CSV into PS_FIU_CUSTOMIZ")
    parser.add_argument("--dsn",      required=True, help="Oracle TNS alias or host:port/service")
    parser.add_argument("--user",     required=True, help="Oracle schema owner (e.g. SYSADM)")
    parser.add_argument("--password", required=True, help="Oracle password")
    parser.add_argument("--csv",      default=None,  help="Path to fiu_customizations.csv (default: same directory as this script)")
    return parser.parse_args()


def main():
    args = parse_args()

    csv_path = args.csv or os.path.join(os.path.dirname(os.path.abspath(__file__)), "fiu_customizations.csv")

    if not os.path.exists(csv_path):
        print(f"ERROR: CSV not found at {csv_path}")
        print("Run find_fiu_customizations.py first to generate it.")
        sys.exit(1)

    # Load CSV
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No rows found in CSV. Nothing to load.")
        sys.exit(0)

    print(f"Loaded {len(rows)} rows from {csv_path}")

    # Connect to Oracle
    try:
        import cx_Oracle
    except ImportError:
        print("ERROR: cx_Oracle is not installed. Run: pip install cx_Oracle")
        sys.exit(1)

    try:
        conn = cx_Oracle.connect(user=args.user, password=args.password, dsn=args.dsn)
    except cx_Oracle.DatabaseError as e:
        print(f"ERROR connecting to Oracle: {e}")
        sys.exit(1)

    cur = conn.cursor()

    # Truncate existing data
    cur.execute("TRUNCATE TABLE PS_FIU_CUSTOMIZ")
    print("Truncated PS_FIU_CUSTOMIZ")

    # Bulk insert
    data = [
        (r["object_type"], r["item_id"], r["objname"])
        for r in rows
    ]

    cur.executemany(
        "INSERT INTO PS_FIU_CUSTOMIZ (OBJECT_TYPE, ITEM_ID, OBJNAME) VALUES (:1, :2, :3)",
        data
    )

    conn.commit()
    print(f"Inserted {len(data)} rows into PS_FIU_CUSTOMIZ")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
