#!/usr/bin/env python3
"""
AWE Workflow Script Generator

Generates PeopleSoft DMS and SQL scripts to copy AWE (Approval Workflow Engine)
workflow definitions between environments.

Usage:
    python generate_awe_scripts.py --process-id FIU_eRAC_APPROVAL --effdt 2020-07-19
    python generate_awe_scripts.py -p FIU_eRAC_APPROVAL -e 2020-07-19 --prev-effdt 2020-07-17
    python generate_awe_scripts.py -p FIU_eRAC_APPROVAL -e "19-JUL-2020" --base-path "N:\\PSDOCS\\HCM_92\\Developers\\Shaun"
    python generate_awe_scripts.py  (interactive prompts if args omitted)

Generated files (written to --output-dir, default: same directory as this script):
    Export_<PROCESS_ID>_Script.dms           -- Data Mover export from source DB
    Import_<PROCESS_ID>_Script.dms           -- Data Mover import to target DB (simple)
    Import_<PROCESS_ID>_FutureDateScript.sql -- Import + date shift to SYSDATE+1

Parameters:
    EOAWPRCS_ID  -- AWE Process ID, e.g. FIU_eRAC_APPROVAL
    EFFDT        -- Effective date of the record to export/import
                   Accepted formats:  YYYY-MM-DD  (e.g. 2020-07-19)
                                      DD-MON-YYYY (e.g. 19-JUL-2020)
    PREV_EFFDT   -- (optional) Previous effective date used to set
                   EOAWDEFN_DEFAULT = 'N' on the old row
"""

import argparse
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASE_PATH = r'N:\PSDOCS\HCM_92\Developers\Shaun'


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date(s):
    """Parse YYYY-MM-DD or DD-MON-YYYY (case-insensitive) into a datetime."""
    s = s.strip().strip("'\"")
    for fmt in ('%Y-%m-%d', '%d-%b-%Y'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"Unrecognised date '{s}'. "
        "Supported formats: YYYY-MM-DD (e.g. 2020-07-19) or DD-MON-YYYY (e.g. 19-JUL-2020)."
    )


def fmt_iso(dt):
    """YYYY-MM-DD  e.g. 2020-07-19"""
    return dt.strftime('%Y-%m-%d')


def fmt_oracle(dt):
    """DD-MON-YYYY  e.g. 19-JUL-2020  (used inside Oracle TO_DATE())"""
    return dt.strftime('%d-%b-%Y').upper()


def fmt_year(dt):
    """Four-digit year string  e.g. '2020'  (used as token in EOAWCRTA_ID INSTR/SUBSTR)"""
    return str(dt.year)


# ---------------------------------------------------------------------------
# Oracle SQL fragment helpers
# ---------------------------------------------------------------------------

def crta_simple(col, yr):
    """
    Replace the year token in an EOAWCRTA_ID column with the new date.
    Used for EOAW_PRCS where there is no -NextID suffix to preserve.
    """
    return (
        f"SUBSTR({col}, 1, INSTR({col}, '{yr}')-1) || TO_CHAR(SYSDATE+1,'YYYY-MM-DD')"
    )


def crta_nextid(col, yr):
    """
    Replace the year token in an EOAWCRTA_ID column with the new date,
    preserving any trailing -NextID suffix.
    Used for EOAW_PATH, EOAW_STEP, EOAWCRTA, EOAWCRTA_REC, EOAWCRTA_VAL.
    """
    return (
        f"SUBSTR({col}, 1, INSTR({col}, '{yr}')-1) || TO_CHAR(SYSDATE+1,'YYYY-MM-DD') || "
        f"(CASE WHEN INSTR({col}, '-NextID') <> 0 "
        f"THEN SUBSTR({col}, INSTR({col}, '-NextID'), LENGTH({col})-1) "
        f"ELSE '' END)"
    )


# ---------------------------------------------------------------------------
# Script generators
# ---------------------------------------------------------------------------

def gen_export_dms(pid, effdt_dt, dat, log):
    """Export DMS — run against the SOURCE database."""
    d = fmt_iso(effdt_dt)
    lines = [
        'SET NO TRACE;',
        f'SET LOG {log};',
        f'SET OUTPUT {dat};',
        '',
        f"EXPORT EOAW_PATH       WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = %DateIn('{d}');",
        f"EXPORT EOAW_PRCS       WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = %DateIn('{d}');",
        f"EXPORT EOAW_STAGE      WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = %DateIn('{d}');",
        f"EXPORT EOAW_STEP       WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = %DateIn('{d}');",
        f"EXPORT EOAW_TIMEOUT    WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = %DateIn('{d}');",
        f"EXPORT EOAW_TIMEOUTDEF WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = %DateIn('{d}');",
        f"EXPORT EOAWCRTA        WHERE EOAWCRTA_ID LIKE '%{pid}%{d}%';",
        f"EXPORT EOAWCRTA_REC    WHERE EOAWCRTA_ID LIKE '%{pid}%{d}%';",
        f"EXPORT EOAWCRTA_VAL    WHERE EOAWCRTA_ID LIKE '%{pid}%{d}%';",
    ]
    return '\n'.join(lines) + '\n'


def gen_import_dms(dat, log):
    """Import DMS — simple import with no date changes, run against the TARGET database."""
    lines = [
        'SET NO TRACE;',
        f'SET LOG {log};',
        f'SET INPUT {dat};',
        'SET UPDATE_DUPS;',
        '',
        'IMPORT *;',
    ]
    return '\n'.join(lines) + '\n'


def gen_future_date_sql(pid, effdt_dt, prev_effdt_dt, dat, log):
    """
    Future-date SQL — shift EFFDT to SYSDATE+1 after import.
    Run against the TARGET database after the Import DMS has completed.
    """
    d     = fmt_iso(effdt_dt)
    d_ora = fmt_oracle(effdt_dt)
    yr    = fmt_year(effdt_dt)

    # EOAWDEFN_DEFAULT = N update for the previous row
    if prev_effdt_dt:
        prev_update = (
            f"UPDATE PS_EOAW_PRCS SET EOAWDEFN_DEFAULT = 'N' "
            f"WHERE EOAWPRCS_ID = '{pid}' "
            f"AND EFFDT = TO_DATE('{fmt_oracle(prev_effdt_dt)}','DD-MON-YYYY');"
        )
    else:
        prev_update = (
            "--- TODO: Replace <DD-MON-YYYY> with the previous effective date before running.\n"
            f"-- UPDATE PS_EOAW_PRCS SET EOAWDEFN_DEFAULT = 'N' "
            f"WHERE EOAWPRCS_ID = '{pid}' "
            f"AND EFFDT = TO_DATE('<DD-MON-YYYY>','DD-MON-YYYY');"
        )

    lines = [
        '--- Delete any rows already sitting at SYSDATE+1 to avoid unique constraint errors.',
        f"--- {pid} is the process identifier embedded in EOAWCRTA_ID.",
        '',
        f"DELETE PS_EOAW_PATH       WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TRUNC(SYSDATE+1);",
        f"DELETE PS_EOAW_PRCS       WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TRUNC(SYSDATE+1);",
        f"DELETE PS_EOAW_STAGE      WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TRUNC(SYSDATE+1);",
        f"DELETE PS_EOAW_STEP       WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TRUNC(SYSDATE+1);",
        f"DELETE PS_EOAW_TIMEOUT    WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TRUNC(SYSDATE+1);",
        f"DELETE PS_EOAW_TIMEOUTDEF WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TRUNC(SYSDATE+1);",
        f"DELETE PS_EOAWCRTA_REC    WHERE EOAWCRTA_ID LIKE '%{pid}%' || TO_CHAR(SYSDATE+1,'YYYY-MM-DD') || '%';",
        f"DELETE PS_EOAWCRTA_VAL    WHERE EOAWCRTA_ID LIKE '%{pid}%' || TO_CHAR(SYSDATE+1,'YYYY-MM-DD') || '%';",
        f"DELETE PS_EOAWCRTA        WHERE EOAWCRTA_ID LIKE '%{pid}%' || TO_CHAR(SYSDATE+1,'YYYY-MM-DD') || '%';",
        '',
        '--- Mark previous Process Definition as non-default (EOAWDEFN_DEFAULT = N).',
        '',
        prev_update,
        '',
        f"--- Shift effective date from {d} to SYSDATE+1.",
        f"--- The year token '{yr}' in EOAWCRTA_ID is replaced with the new YYYY-MM-DD date.",
        '',
        (f"UPDATE PS_EOAW_PATH A "
         f"SET EFFDT = TRUNC(SYSDATE+1), "
         f"EOAWCRTA_ID = {crta_nextid('A.EOAWCRTA_ID', yr)} "
         f"WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TO_DATE('{d_ora}','DD-MON-YYYY');"),
        '',
        (f"UPDATE PS_EOAW_PRCS A "
         f"SET EFFDT = TRUNC(SYSDATE+1), "
         f"A.EOAWCRTA_ID = {crta_simple('A.EOAWCRTA_ID', yr)}, "
         f"A.EOAWDEFN_CRTA_ID = {crta_simple('A.EOAWCRTA_ID', yr)} "
         f"WHERE A.EOAWPRCS_ID = '{pid}' AND A.EFFDT = TO_DATE('{d_ora}','DD-MON-YYYY');"),
        '',
        (f"UPDATE PS_EOAW_STAGE "
         f"SET EFFDT = TRUNC(SYSDATE+1) "
         f"WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TO_DATE('{d_ora}','DD-MON-YYYY');"),
        '',
        (f"UPDATE PS_EOAW_STEP A "
         f"SET EFFDT = TRUNC(SYSDATE+1), "
         f"EOAWSELF_CRTA_ID = {crta_nextid('A.EOAWSELF_CRTA_ID', yr)}, "
         f"EOAWCRTA_ID = {crta_nextid('A.EOAWCRTA_ID', yr)} "
         f"WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TO_DATE('{d_ora}','DD-MON-YYYY');"),
        '',
        (f"UPDATE PS_EOAW_TIMEOUT "
         f"SET EFFDT = TRUNC(SYSDATE+1) "
         f"WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TO_DATE('{d_ora}','DD-MON-YYYY');"),
        '',
        (f"UPDATE PS_EOAW_TIMEOUTDEF "
         f"SET EFFDT = TRUNC(SYSDATE+1) "
         f"WHERE EOAWPRCS_ID = '{pid}' AND EFFDT = TO_DATE('{d_ora}','DD-MON-YYYY');"),
        '',
        (f"UPDATE PS_EOAWCRTA_REC A "
         f"SET EOAWCRTA_ID = {crta_nextid('A.EOAWCRTA_ID', yr)} "
         f"WHERE EOAWCRTA_ID LIKE '%{pid}%{d}%';"),
        '',
        (f"UPDATE PS_EOAWCRTA_VAL A "
         f"SET EOAWCRTA_ID = {crta_nextid('A.EOAWCRTA_ID', yr)} "
         f"WHERE EOAWCRTA_ID LIKE '%{pid}%{d}%';"),
        '',
        (f"UPDATE PS_EOAWCRTA A "
         f"SET A.EOAWCRTA_ID = {crta_nextid('A.EOAWCRTA_ID', yr)} "
         f"WHERE A.EOAWCRTA_ID LIKE '%{pid}%{d}%';"),
        '',
    ]
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def prompt_missing(args):
    """Interactively prompt for required values if not supplied on the command line."""
    if not args.process_id:
        args.process_id = input('EOAWPRCS_ID (e.g. FIU_eRAC_APPROVAL): ').strip()
    if not args.effdt:
        args.effdt = input('EFFDT (e.g. 2020-07-19 or 19-JUL-2020): ').strip()


def main():
    parser = argparse.ArgumentParser(
        description='Generate PeopleSoft DMS/SQL scripts for copying AWE workflow between environments.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--process-id', '-p',
                        help='EOAWPRCS_ID value (e.g. FIU_eRAC_APPROVAL)')
    parser.add_argument('--effdt', '-e',
                        help='Effective date: YYYY-MM-DD or DD-MON-YYYY (e.g. 2020-07-19)')
    parser.add_argument('--prev-effdt',
                        help='Previous effective date for EOAWDEFN_DEFAULT=N update (optional)')
    parser.add_argument('--base-path', default=DEFAULT_BASE_PATH,
                        help=f'Base path for DMS log/dat files (default: {DEFAULT_BASE_PATH})')
    parser.add_argument('--output-dir', '-o', default=SCRIPT_DIR,
                        help='Directory to write generated scripts (default: script directory)')

    args = parser.parse_args()
    prompt_missing(args)

    if not args.process_id or not args.effdt:
        parser.error('--process-id and --effdt are required.')

    try:
        effdt_dt = parse_date(args.effdt)
    except ValueError as e:
        sys.exit(f'Error: {e}')

    prev_effdt_dt = None
    if args.prev_effdt:
        try:
            prev_effdt_dt = parse_date(args.prev_effdt)
        except ValueError as e:
            sys.exit(f'Error (--prev-effdt): {e}')

    pid  = args.process_id
    base = args.base_path
    outd = args.output_dir
    dp   = os.path.join(base, f'AWE_{pid}.dat')
    lp   = os.path.join(base, f'AWE_{pid}_log.log')

    os.makedirs(outd, exist_ok=True)

    files = {
        f'Export_{pid}_Script.dms':           gen_export_dms(pid, effdt_dt, dp, lp),
        f'Import_{pid}_Script.dms':           gen_import_dms(dp, lp),
        f'Import_{pid}_FutureDateScript.sql': gen_future_date_sql(pid, effdt_dt, prev_effdt_dt, dp, lp),
    }

    print()
    for name, content in files.items():
        dest = os.path.join(outd, name)
        with open(dest, 'w', newline='\r\n') as fh:
            fh.write(content)
        print(f'  Created: {dest}')

    print()
    print(f'  Process ID : {pid}')
    print(f'  EFFDT      : {fmt_iso(effdt_dt)}  ({fmt_oracle(effdt_dt)})  year token = {fmt_year(effdt_dt)}')
    if prev_effdt_dt:
        print(f'  Prev EFFDT : {fmt_iso(prev_effdt_dt)}  ({fmt_oracle(prev_effdt_dt)})')
    else:
        print(f'  Prev EFFDT : not provided — EOAWDEFN_DEFAULT update left as TODO comment')
    print(f'  Dat file   : {dp}')
    print(f'  Log file   : {lp}')
    print()


if __name__ == '__main__':
    main()
