/* =============================================================
   FIU_RETROFIT  –  PROC_LOOP  (Section Select)
   Drives the looping section.  Each row fetched populates the
   state record fields listed in the App Designer bind mapping:
     Column 1  →  FIU_RFTR_AET.AE_OBJECT_TYPE
     Column 2  →  FIU_RFTR_AET.AE_ITEM_ID
     Column 3  →  FIU_RFTR_AET.AE_OBJNAME
     Column 4  →  FIU_RFTR_AET.AE_SEQNO
   ============================================================= */

SELECT OBJECT_TYPE,
       ITEM_ID,
       OBJNAME,
       SEQNO
FROM   PS_FIU_RFTR_STG
WHERE  PROCESS_INSTANCE = %BIND(PROCESS_INSTANCE)
AND    PROCESS_STATUS   = 'P'
ORDER BY SEQNO
