/* =============================================================
   FIU_RETROFIT  –  MAIN.STEP02  (SQL Action)
   Loads PS_FIU_CUSTOMIZ into the staging table for this
   process instance.  Applies the optional object-type filter
   stored in the state record (OBJ_TYPE_FLT).
   Blank filter = process all object types.
   ============================================================= */

INSERT INTO PS_FIU_RFTR_STG
    (PROCESS_INSTANCE, SEQNO, OBJECT_TYPE, ITEM_ID,
     OBJNAME, PROCESS_STATUS, ERROR_MSG)
SELECT
    %BIND(PROCESS_INSTANCE),
    ROWNUM,
    OBJECT_TYPE,
    ITEM_ID,
    OBJNAME,
    'P',
    ' '
FROM PS_FIU_CUSTOMIZ
WHERE (%BIND(OBJ_TYPE_FLT) = ' '
   OR  OBJECT_TYPE = %BIND(OBJ_TYPE_FLT))
ORDER BY OBJECT_TYPE, ITEM_ID
