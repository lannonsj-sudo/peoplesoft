# FIU_RETROFIT – PeopleSoft App Engine

Copies FIU PeopleCode customizations from the current (source)
database to the upgraded (target) database via an Oracle DB link.
The list of customizations is driven by the output of
`find_fiu_customizations.py`.

---

## Architecture

```
fiu_customizations.csv
        │
        ▼  load_to_ps.py
PS_FIU_CUSTOMIZ  (Oracle table in source DB)
        │
        ▼  FIU_RETROFIT App Engine
PS_FIU_RFTR_STG  (staging / audit trail)
        │
        ▼  Oracle DB Link
PSPCMPROG / PSPCMTXT      ← standard PeopleCode tables in target DB
PSAEPCMPROG / PSAEPCMTXT  ← App Engine PeopleCode tables in target DB
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| Oracle DB link | Created in source DB pointing to target DB schema (see `sql/02_create_dblink_template.sql`) |
| Tables created | Run `sql/01_create_tables.sql` in the source DB |
| CSV loaded | Run `find_fiu_customizations.py`, then `load_to_ps.py` |
| App Designer access | Required to build the App Engine and records |

---

## Step 1 – Create the Oracle DB Link

```sql
-- Run on the SOURCE database as the PS schema owner
CREATE DATABASE LINK UPGRD_LINK
    CONNECT TO SYSADM
    IDENTIFIED BY "sysadm"
    USING 'HR92UPGRD';

-- Verify
SELECT 1 FROM DUAL@UPGRD_LINK;
```

---

## Step 2 – Create Supporting Tables

Run `sql/01_create_tables.sql` in the source database via Data Mover
or SQL*Plus. This creates:

- `PS_FIU_CUSTOMIZ` – input list of FIU customizations
- `PS_FIU_RFTR_RC` – run control
- `PS_FIU_RFTR_STG` – per-run processing log

---

## Step 3 – Load the Customization List

```bash
# Generate the CSV from compare report XML files
python find_fiu_customizations.py

# Load CSV into PS_FIU_CUSTOMIZ
python load_to_ps.py --dsn HR90SRC --user SYSADM --password sysadm
```

---

## Step 4 – Build the App Engine in App Designer

### Records

| Record Name   | Type         | Description |
|---|---|---|
| FIU_RFTR_RC   | SQL Table    | Run control (OPRID, RUN_CNTL_ID, DBLINK_NAME, OBJ_TYPE_FLT) |
| FIU_RFTR_STG  | SQL Table    | Staging / audit (see DDL) |
| FIU_RFTR_AET  | Derived/Work | App Engine state record (no table) |
| FIU_CUSTOMIZ  | SQL Table    | Input list (created by load_to_ps.py) |

**FIU_RFTR_AET field list** (Derived/Work – no physical table):

| Field | Type | Length | Purpose |
|---|---|---|---|
| PROCESS_INSTANCE | Number | 10 | System |
| RUN_CNTL_ID | Char | 30 | From run control |
| DBLINK_NAME | Char | 30 | Oracle DB link name |
| OBJ_TYPE_FLT | Char | 50 | Optional object type filter |
| AE_OBJECT_TYPE | Char | 50 | Loop bind – current object type |
| AE_ITEM_ID | Char | 100 | Loop bind – current item ID |
| AE_OBJNAME | Char | 254 | Loop bind – current objname |
| AE_SEQNO | Number | 10 | Loop bind – staging sequence |
| AE_COPIED | Number | 10 | Running count of copied items |
| AE_ERRORS | Number | 10 | Running count of errors |
| AE_SKIPPED | Number | 10 | Running count of skipped items |

---

### App Engine Program: FIU_RETROFIT

**Program Properties**
- Type: Standard
- State Record: FIU_RFTR_AET
- Disable Restart: Yes (staging table provides audit trail)

---

### Section / Step Layout

```
MAIN  (Default section, not looping)
├── STEP01  OnExecute PeopleCode  →  peoplecode/MAIN_INIT.ppc
├── STEP02  SQL Action            →  peoplecode/MAIN_LOAD.sql
├── STEP03  Call Section          →  PROC_LOOP
└── STEP04  OnExecute PeopleCode  →  peoplecode/MAIN_FINALIZE.ppc

PROC_LOOP  (Looping section)
├── Select SQL  →  peoplecode/PROC_LOOP_SELECT.sql
│     Bind map:
│       Column 1  →  FIU_RFTR_AET.AE_OBJECT_TYPE
│       Column 2  →  FIU_RFTR_AET.AE_ITEM_ID
│       Column 3  →  FIU_RFTR_AET.AE_OBJNAME
│       Column 4  →  FIU_RFTR_AET.AE_SEQNO
└── STEP01  OnExecute PeopleCode  →  peoplecode/PROC_LOOP_COPY.ppc
```

---

### PeopleCode Files

| File | Section.Step | Purpose |
|---|---|---|
| `MAIN_INIT.ppc` | MAIN.STEP01 | Read run control, validate DB link |
| `MAIN_LOAD.sql` | MAIN.STEP02 | Populate staging from PS_FIU_CUSTOMIZ |
| `PROC_LOOP_SELECT.sql` | PROC_LOOP (select) | Drive the loop over pending rows |
| `PROC_LOOP_COPY.ppc` | PROC_LOOP.STEP01 | Copy PeopleCode via DB link |
| `MAIN_FINALIZE.ppc` | MAIN.STEP04 | Log summary and skipped items |

---

## Step 5 – Create the Run Control Page

Create a simple page bound to `FIU_RFTR_RC` with fields:
- `DBLINK_NAME` – Oracle DB link name (required)
- `OBJ_TYPE_FLT` – Object type filter (optional; blank = all)

Add the component to a menu and assign security as needed.

---

## Step 6 – Run

1. Open the FIU Retrofit run control page.
2. Enter the DB link name (e.g. `UPGRD_LINK`).
3. Optionally enter an object type filter (e.g. `Record PeopleCode`).
4. Submit the process via Process Scheduler.
5. Review `PS_FIU_RFTR_STG` after completion:

```sql
-- Summary
SELECT PROCESS_STATUS, COUNT(*) AS CNT
FROM   PS_FIU_RFTR_STG
WHERE  PROCESS_INSTANCE = <your_instance>
GROUP BY PROCESS_STATUS;

-- Errors
SELECT OBJECT_TYPE, ITEM_ID, ERROR_MSG
FROM   PS_FIU_RFTR_STG
WHERE  PROCESS_INSTANCE = <your_instance>
AND    PROCESS_STATUS = 'E';

-- Skipped (manual migration needed)
SELECT OBJECT_TYPE, ITEM_ID
FROM   PS_FIU_RFTR_STG
WHERE  PROCESS_INSTANCE = <your_instance>
AND    PROCESS_STATUS = 'S';
```

---

## Object Type Handling

| Object Type | Automated | Method |
|---|---|---|
| Record PeopleCode | Yes | PSPCMPROG + PSPCMTXT via DB link |
| Component PeopleCode | Yes | PSPCMPROG + PSPCMTXT via DB link |
| Component Record PeopleCode | Yes | PSPCMPROG + PSPCMTXT via DB link |
| Component Rec Fld PeopleCode | Yes | PSPCMPROG + PSPCMTXT via DB link |
| Page PeopleCode | Yes | PSPCMPROG + PSPCMTXT via DB link |
| Application Package PeopleCode | Yes | PSPCMPROG + PSPCMTXT via DB link |
| Application Engine PeopleCode | Yes | PSAEPCMPROG + PSAEPCMTXT via DB link |
| Application Engine Programs | Yes | PSAEPCMPROG + PSAEPCMTXT via DB link |
| Application Engine Sections | Yes | PSAEPCMPROG + PSAEPCMTXT via DB link |
| Records | Skipped | App Designer Copy Project |
| Pages | Skipped | App Designer Copy Project |
| Components | Skipped | App Designer Copy Project |
| Portal Registry Structures | Skipped | App Designer Copy Project |
| URL Definitions | Skipped | App Designer Copy Project |

---

## Important Notes

- **Always take a full backup of the target database before running.**
- After copying PeopleCode, **recompile all PeopleCode** in the target
  environment using App Designer (Build > PeopleCode Compile All) or
  the command-line `pscbo` tool. Recompilation resolves any token
  references that changed between PeopleTools versions.
- Skipped items (Records, Pages, etc.) should be migrated via an
  App Designer project using File > Copy Project From File or
  Tools > Copy Project > To Database.
- The App Engine copies the **entire PeopleCode program** for each
  matched primary object — not just the FIU-modified events. Review
  the results before promoting to production.
