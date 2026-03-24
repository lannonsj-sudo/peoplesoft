"""
Analyze page_ci_struc.xml and epaf.xml to produce a field mapping
for the BI Publisher RTF template.
"""
import xml.etree.ElementTree as ET
import re

# ── 1. Parse page_ci_struc.xml ────────────────────────────────────────────────
pci_tree = ET.parse(r"C:\Users\shaun\Claude\BI_Templates\page_ci_struc.xml")
pci_root = pci_tree.getroot()

page_fields = []   # list of dicts
for row in pci_root.findall(".//ROW"):
    rec = {col.get("NAME"): (col.text or "").strip()
           for col in row.findall("COLUMN")}
    page_fields.append({
        "pnlname":   rec.get("PNLNAME", ""),
        "bcitem":    rec.get("BCITEMNAME", ""),
        "recname":   rec.get("RECNAME", ""),
        "fieldname": rec.get("FIELDNAME", ""),
        "label":     rec.get("LBLTEXT", ""),
        "fielduse":  rec.get("FIELDUSE", ""),
        "fieldnum":  rec.get("FIELDNUM", ""),
    })

print(f"Total page fields: {len(page_fields)}")
print()

# ── 2. Parse epaf.xml – build a map of element_name → parent_section ─────────
epaf_tree = ET.parse(r"C:\Users\shaun\Claude\BI_Templates\epaf.xml")
epaf_root = epaf_tree.getroot()

# Walk the XML and record where each element lives
# Structure: FIU_EF_ENTRY > {section} > ROW_{section} > fields
#        or: FIU_EF_ENTRY > {section} > ROW_{section} > {sub} > ROW_{sub} > fields
field_location = {}   # bcitemname → (section_path, xpath_for_bip)

def walk(node, path_parts):
    for child in node:
        tag = child.tag
        child_path = path_parts + [tag]
        # If this is a leaf (has text content, no children with content)
        children = list(child)
        if not children or all(c.text is None or c.text.strip() == "" for c in children):
            # It's effectively a field
            if tag not in field_location:
                field_location[tag] = "/".join(path_parts)
        walk(child, child_path)

walk(epaf_root, [epaf_root.tag])

# ── 3. Match page fields to XML locations ────────────────────────────────────
print("=" * 90)
print(f"{'BCITEMNAME':<30} {'LABEL':<35} {'RECNAME':<25} {'XML PARENT'}")
print("=" * 90)

for f in page_fields:
    bc   = f["bcitem"]
    loc  = field_location.get(bc, "NOT FOUND IN XML")
    print(f"{bc:<30} {f['label']:<35} {f['recname']:<25} {loc}")

# ── 4. Group fields by XML section ───────────────────────────────────────────
print()
print("=" * 90)
print("FIELDS GROUPED BY XML SECTION")
print("=" * 90)

from collections import defaultdict
by_section = defaultdict(list)
for f in page_fields:
    bc  = f["bcitem"]
    loc = field_location.get(bc, "NOT FOUND IN XML")
    by_section[loc].append((bc, f["label"], f["recname"]))

for section, fields in sorted(by_section.items()):
    print(f"\n  [{section}]")
    for bc, lbl, rec in fields:
        print(f"    {bc:<30} label='{lbl}'  recname={rec}")
