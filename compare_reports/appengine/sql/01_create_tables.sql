-- =============================================================
-- FIU_RETROFIT App Engine - Supporting Table DDL (Oracle)
-- Create these tables via Data Mover or SQL*Plus before
-- defining the Records in App Designer.
-- =============================================================

-- -----------------------------------------------------------
-- PS_FIU_CUSTOMIZ
-- Populated by load_to_ps.py from fiu_customizations.csv.
-- Serves as the master list of FIU customizations to retrofit.
-- -----------------------------------------------------------
CREATE TABLE PS_FIU_CUSTOMIZ (
    OBJECT_TYPE   VARCHAR2(50)  NOT NULL,
    ITEM_ID       VARCHAR2(100) NOT NULL,
    OBJNAME       VARCHAR2(254) NOT NULL
);

CREATE UNIQUE INDEX PSFIU_CUSTOMIZ
    ON PS_FIU_CUSTOMIZ (OBJECT_TYPE, ITEM_ID);


-- -----------------------------------------------------------
-- PS_FIU_RFTR_RC  (Run Control)
-- One row per OPRID / RUN_CNTL_ID pair.
-- DBLINK_NAME  = Oracle DB link name pointing to the
--               upgraded (target) database.
-- OBJ_TYPE_FLT = Optional filter; leave blank to process all
--               object types, or enter an exact OBJECT_TYPE
--               value (e.g. "Record PeopleCode") to limit scope.
-- -----------------------------------------------------------
CREATE TABLE PS_FIU_RFTR_RC (
    OPRID         VARCHAR2(30)  NOT NULL,
    RUN_CNTL_ID   VARCHAR2(30)  NOT NULL,
    DBLINK_NAME   VARCHAR2(30)  NOT NULL,
    OBJ_TYPE_FLT  VARCHAR2(50)  NOT NULL
);

CREATE UNIQUE INDEX PSFIU_RFTR_RC
    ON PS_FIU_RFTR_RC (OPRID, RUN_CNTL_ID);


-- -----------------------------------------------------------
-- PS_FIU_RFTR_STG  (Processing Staging)
-- One row per customization item per process instance.
-- PROCESS_STATUS values:
--   P = Pending
--   C = Completed
--   E = Error
--   S = Skipped (object type not handled automatically)
-- -----------------------------------------------------------
CREATE TABLE PS_FIU_RFTR_STG (
    PROCESS_INSTANCE  DECIMAL(10,0)  NOT NULL,
    SEQNO             DECIMAL(10,0)  NOT NULL,
    OBJECT_TYPE       VARCHAR2(50)   NOT NULL,
    ITEM_ID           VARCHAR2(100)  NOT NULL,
    OBJNAME           VARCHAR2(254)  NOT NULL,
    PROCESS_STATUS    VARCHAR2(1)    NOT NULL,
    ERROR_MSG         VARCHAR2(254)  NOT NULL
);

CREATE UNIQUE INDEX PSFIU_RFTR_STG
    ON PS_FIU_RFTR_STG (PROCESS_INSTANCE, SEQNO);


-- -----------------------------------------------------------
-- FIU_RFTR_AET  (App Engine State Record)
-- Defined in App Designer as a Derived/Work record —
-- no physical table is created for it.
-- Fields required:
--   PROCESS_INSTANCE  Number(10,0)
--   RUN_CNTL_ID       Char(30)
--   DBLINK_NAME       Char(30)
--   OBJ_TYPE_FLT      Char(50)
--   AE_OBJECT_TYPE    Char(50)   -- bound from PROC_LOOP select
--   AE_ITEM_ID        Char(100)  -- bound from PROC_LOOP select
--   AE_OBJNAME        Char(254)  -- bound from PROC_LOOP select
--   AE_SEQNO          Number(10,0)
--   AE_COPIED         Number(10,0)
--   AE_ERRORS         Number(10,0)
--   AE_SKIPPED        Number(10,0)
-- -----------------------------------------------------------
