"""
Scan PeopleSoft compare report XML files for FIU references.
Searches all text content within each <item> for 'FIU', then outputs
the item's object_type, item_id, and objname values.

Output CSV columns: object_type, item_id, objname
"""

import csv
import os
import xml.etree.ElementTree as ET


def iter_items_with_fiu(xml_path):
    """Parse an XML file and yield (object_type, item_id, objname)
    for each <item> that contains 'FIU' anywhere in its text content."""

    object_type_name = ""
    item_id = ""
    objnames = []
    has_fiu = False
    item_depth = 0
    in_item = False

    context = ET.iterparse(xml_path, events=("start", "end"))

    for event, elem in context:
        if event == "start":
            if elem.tag == "object_type":
                object_type_name = elem.get("name", "")
            elif elem.tag == "item" and not in_item:
                item_id = elem.get("id", "")
                objnames = []
                has_fiu = False
                item_depth = 1
                in_item = True
                if "FIU" in item_id.upper():
                    has_fiu = True
            elif in_item:
                item_depth += 1

        elif event == "end":
            if in_item:
                # Collect text from every element inside the item
                text = (elem.text or "").strip()
                tail = (elem.tail or "").strip()
                if "FIU" in text.upper() or "FIU" in tail.upper():
                    has_fiu = True

                if elem.tag == "objname" and text:
                    objnames.append(text)

                if elem.tag == "item":
                    item_depth -= 1
                    if item_depth == 0:
                        in_item = False
                        if has_fiu:
                            yield (object_type_name, item_id, "|".join(objnames))
                        elem.clear()
                else:
                    item_depth -= 1
            else:
                elem.clear()


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PS_Compare")
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fiu_customizations.csv")

    results = []
    seen = set()

    for root, dirs, files in os.walk(base_dir):
        for filename in sorted(files):
            if not filename.endswith(".xml"):
                continue
            if filename == "index.xml":
                continue

            filepath = os.path.join(root, filename)
            print(f"Processing: {filepath}")

            try:
                for object_type, item_id, objname in iter_items_with_fiu(filepath):
                    key = (object_type, item_id)
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "object_type": object_type,
                            "item_id": item_id,
                            "objname": objname,
                        })
            except ET.ParseError as e:
                print(f"  XML parse error: {e}")
            except Exception as e:
                print(f"  Error: {e}")

    results.sort(key=lambda r: (r["object_type"], r["item_id"]))

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["object_type", "item_id", "objname"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nDone! Found {len(results)} FIU customizations.")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
