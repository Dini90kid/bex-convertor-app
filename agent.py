# ----------------------------
# agent.py (Clean, Working)
# ----------------------------

from pathlib import Path
import json
import re
import csv

# ----------------------------
# Helper READ/WRITE
# ----------------------------
def _read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except:
        return path.read_text(encoding="latin-1", errors="ignore")

def _write_json(obj, path: Path):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def _write_md(text, path: Path):
    path.write_text(text, encoding="utf-8")

def _write_csv(rows, headers, path: Path):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)

# ----------------------------
# Overrides Loader
# ----------------------------
def load_overrides(folder: Path):
    p = folder / "char_map_overrides.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            return {}
    return {}

# ----------------------------
# Parse GP Text
# ----------------------------
def parse_gp_text(text: str, overrides: dict):
    lines = text.splitlines()
    
    # Metadata
    rep = re.search(r"REPORT:\s*(\S+)", text)
    cube = re.search(r"INFOCUBE\.*:\s*(\S+)", text)
    
    spec = {
        "query_name": rep.group(1) if rep else "UNKNOWN",
        "infocube": cube.group(1) if cube else "UNKNOWN",
        "characteristics": [],
        "key_figures": [],
        "move_blocks": {}
    }
    
    # Find characteristics
    for m in re.finditer(r"FORM\s+A_S_(\d+)", text):
        tid = m.group(1)
        block = extract_block(text, f"A_S_{tid}")
        spec["characteristics"].append({
            "tech_id": tid,
            "infoobject": overrides.get(tid, f"CHAR_{tid}"),
            "variables": {
                "ranges": extract_ranges(block),
                "single": extract_singles(block)
            }
        })
    
    # Find key figures
    kf = set()
    for ln in lines:
        for m in re.findall(r"Z[A-Z0-9_]{5,}", ln):
            kf.add(m)
    spec["key_figures"] = sorted(kf)
    
    # MOVE_Z_SP blocks
    for m in re.finditer(r"MOVE_Z_SP_(\d+)", text):
        name = f"MOVE_Z_SP_{m.group(1)}"
        spec["move_blocks"][name] = extract_block(text, name)
    
    return spec

# ----------------------------
# Extract FORM block
# ----------------------------
def extract_block(text: str, form_name: str):
    pat = rf"FORM\s+{form_name}\b(.+?)ENDFORM\."
    m = re.search(pat, text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""

# ----------------------------
# Extract Variables
# ----------------------------
def extract_ranges(block: str):
    ls = re.findall(r"LS(\d+)", block)
    hs = re.findall(r"HS(\d+)", block)
    return [[f"LS{a}", f"HS{b}"] for a, b in zip(ls, hs)]

def extract_singles(block: str):
    return f"LK{m}" for m in re.findall(r"L[SK", block)]

# ----------------------------
# Markdown Generation
# ----------------------------
def generate_doc(spec: dict, notes: str = ""):
    md = []
    md.append(f"# Query: {spec['query_name']}")
    md.append(f"**InfoProvider:** {spec['infocube']}")
    md.append("")
    md.append("## Characteristics")
    for c in spec["characteristics"]:
        md.append(f"- {c['infoobject']} (Tech ID {c['tech_id']})")
        md.append(f"  - Ranges: {c['variables']['ranges']}")
        md.append(f"  - Single: {c['variables']['single']}")
    md.append("")
    md.append("## Key Figures")
    for k in spec["key_figures"]:
        md.append(f"- {k}")
    md.append("")
    if notes:
        md.append("## Notes")
        md.append(notes)
    return "\n".join(md)

# ----------------------------
# Test Data Generator
# ----------------------------
def generate_testdata(spec: dict):
    headers = []
    rows = []
    
    # headers
    for c in spec["characteristics"]:
        headers.append(c["infoobject"])
    for k in spec["key_figures"]:
        headers.append(k)
    
    # 5 rows
    for i in range(5):
        row = []
        for c in spec["characteristics"]:
            row.append(f"{c['infoobject']}_{i+1}")
        for k in spec["key_figures"]:
            row.append(i + 1)
        rows.append(row)
    
    return headers, rows

# ----------------------------
# PROCESS A GP FILE
# ----------------------------
def process_gp_file(path: Path, overrides: dict, out_dir: Path):
    text = _read_text(path)
    spec = parse_gp_text(text, overrides)
    
    # JSON
    _write_json(spec, out_dir / f"{path.stem}_spec.json")
    
    # MD
    md = generate_doc(spec)
    _write_md(md, out_dir / f"{path.stem}_documentation.md")
    
    # CSV
    headers, rows = generate_testdata(spec)
    _write_csv(rows, headers, out_dir / f"{path.stem}_testdata.csv")
