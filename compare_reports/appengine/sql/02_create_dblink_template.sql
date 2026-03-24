-- =============================================================
-- DB Link Template
-- Run this on the SOURCE (current) database as the PS schema
-- owner.  Replace the placeholders with real values.
-- The link name entered here must match DBLINK_NAME in the
-- FIU_RETROFIT run control page.
-- =============================================================

CREATE DATABASE LINK <LINK_NAME>
    CONNECT TO <TARGET_PS_SCHEMA>
    IDENTIFIED BY "<TARGET_PASSWORD>"
    USING '<TARGET_TNS_ALIAS>';

-- Example:
-- CREATE DATABASE LINK UPGRD_LINK
--     CONNECT TO SYSADM
--     IDENTIFIED BY "sysadm"
--     USING 'HRPRD92';

-- Verify connectivity before running the App Engine:
SELECT 1 FROM DUAL@<LINK_NAME>;
