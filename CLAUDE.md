# CLAUDE.md — PeopleSoft/Oracle Project Standards

## Project Overview
This repository contains PeopleSoft application development artifacts including
Application Engine programs, SQR reports, BI Publisher templates, Integration
Broker configurations, and supporting SQL/PeopleCode.

Environment: PeopleSoft HCM on Oracle DB, Linux app/process scheduler servers.

---

## Repository Structure
```
/AE/          - Application Engine programs (.xml exports)
/SQR/         - SQR report source files (.sqr, .sqc)
/BIP/         - BI Publisher report definitions and RTF templates
/SQL/         - Standalone SQL scripts (DDL, DML, utility queries)
/IB/          - Integration Broker node/service/handler configs
/PEOPLECODE/  - Standalone PeopleCode exports
/SCHEMA/      - PS metadata queries, record/field definitions
```

---

## Database Conventions (Oracle)

- All SQL must be Oracle-compatible. No T-SQL, no MySQL syntax.
- Use `SYSDATE` not `GETDATE()` or `NOW()`.
- Use `NVL()` not `ISNULL()` or `COALESCE()` (prefer NVL for PS consistency).
- String concatenation uses `||` not `+`.
- Use `ROWNUM` or `FETCH FIRST n ROWS ONLY` for row limiting (12c+).
- Bind variables use `:bindvar` syntax in native SQL; use `%BIND()` in PS SQL.
- All PS tables are prefixed: `PS_` for data tables, `PSPT_` for temp tables.
- Never SELECT * — always name columns explicitly.
- Use `LISTAGG(col, ', ') WITHIN GROUP (ORDER BY col)` for string aggregation.

---

## PeopleCode Standards

- Use `&` prefix for all local variables: `&strName`, `&rowCount`, `&rs`.
- Declare all variables explicitly — avoid implicit typing.
- Use `SQLExec()` for single-row selects; use `CreateSQL()` for loops.
- Always call `&sql.Close()` after `CreateSQL()` loops.
- Error handling: wrap risky operations in `try/catch`, log via `%Message`.
- Avoid hardcoded Business Unit or SetID values — use `%BusinessUnit`, `%SetID`.
- Use `%Table(RECORD_NAME)` instead of hardcoded `PS_RECORD_NAME` in SQL strings.

---

## Application Engine Standards

- Program naming: `<PREFIX>_<FUNCTION>` (e.g., `HR_LOAD_STG`).
- Use `%UpdateStats` after large inserts into staging tables.
- Restart logic: mark steps as Restart=Yes only when idempotent.
- Use `%Truncate` for staging table cleanup rather than DELETE with no WHERE.
- Commit strategy: commit at logical boundaries, not every step.
- AE SQL steps: prefer `%Insert`, `%Update`, `%Delete` meta-SQL where applicable.
- State records: document all fields used in the State Record in comments.

---

## SQR Standards

- Always include `#include 'setenv.sqc'` and `#include 'stdapi.sqc'`.
- Use `#define` for constants at the top of the file.
- Report parameters come in via `PRCSRUNCNTL` — read via `do Get-Run-Control`.
- Date formatting: use `do Format-DateTime` from `datetime.sqc`.
- Output: default to `FILEIO` via Process Scheduler output type.
- Avoid hardcoded file paths — use `$prcs_process_instance` for dynamic naming.
- Compile flags: use `-ZIf` for if/else optimization; `-printer:ht` for HTML out.

---

## BI Publisher Standards

- Use native BIP syntax: `<?field_name?>`, `<?for-each:ROW?>`, `<?end for-each?>`.
- Do NOT use Word MERGEFIELD codes (`«field»`) — native BIP tags only.
- XPath string functions: `substring()`, `string-length()`, `translate()`.
- Conditional blocks: `<?if:FIELD='VALUE'?>` ... `<?end if?>`.
- Date formatting in template: `<?format-date:DATE_FIELD,'MM/DD/YYYY'?>`.
- RTF templates must be tested against the actual XML data file before commit.
- Always include a sample XML data file in `/BIP/<report>/` for testing.

---

## Integration Broker Standards

- Node naming convention: document the local node name and target node in comments.
- Service Operations: note whether sync, async, or async with callback.
- Handler PeopleCode: log inbound/outbound payloads to IB log at debug level.
- Connector properties: do not hardcode URLs — use Gateway URL configuration.
- SAML/auth tokens: never commit real tokens or passwords to the repo.
- Freemarker transforms: document input schema and output schema in the header.

---

## SQL Script Standards

- Every script must have a header block:
```sql
  -- Script:   <filename>.sql
  -- Purpose:  <one line description>
  -- Tables:   <PS tables touched>
  -- Author:   <initials>
  -- Modified: <YYYY-MM-DD>
```
- All DML scripts must begin with a SELECT to verify target rows before changes.
- End every DML script with a `COMMIT;` or explicit `ROLLBACK;` comment noting intent.
- Metadata queries against PSQRYDEFN, PSQRYCRITERIA, PSQRYRECORD, PSQRYFIELD
  should include comments explaining what PS Query they reconstruct.

---

## Code Review Checklist

When reviewing PRs, check for:
- [ ] No hardcoded environment values (BU, SetID, server paths, URLs)
- [ ] No SELECT * statements
- [ ] All SQL is Oracle-compatible
- [ ] AE steps have appropriate restart/commit strategy noted
- [ ] SQR includes required standard includes
- [ ] BIP templates use native syntax only
- [ ] IB handlers have logging at debug level
- [ ] SQL scripts have header block
- [ ] No credentials, tokens, or passwords in any file

---

## What Claude Should NOT Do

- Do not suggest SQL Server or MySQL syntax.
- Do not suggest `COALESCE` where `NVL` is the established pattern.
- Do not rewrite PeopleCode to JavaScript or Python equivalents.
- Do not remove `%Table()` wrappers and replace with hardcoded table names.
- Do not suggest ORM patterns — direct SQL is standard in this environment.
