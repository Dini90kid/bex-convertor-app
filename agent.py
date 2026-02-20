# ---------------------------------------------------------
# agent.py  (Clean, Syntax-error-free BEx GP Processor)
# ---------------------------------------------------------

from pathlib import Path
import json
import re
import csv


# ---------------------------------------------------------
# BASIC READ/WRITE HELPERS
# ---------------------------------------------------------
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
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


# ---------------------------------------------------------
# OVERRIDES LOADER
# ---------------------------------------------------------
def load_overrides(folder: Path):
    ov_path = folder / "char_map_overrides.json"
    if ov_path.exists():
        try:
            return json.loads(ov_path.read_text())
        except:
            return {}
    return {}


# ---------------------------------------------------------
# PARSE GP TEXT
# ---------------------------------------------------------
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

    # CHARACTERISTICS via A_S_ blocks
    for m in re.finditer(r"FORM\s+A_S_(\d+)", text):
        tech = m.group(1)
        block = extract_block(text, f"A_S_{tech}")
        spec["characteristics"].append({
            "tech_id": tech,
            "infoobject": overrides.get(tech, f"CHAR_{tech}"),
            "variables": {
                "ranges": extract_ranges(block),
                "single": extract_singles(block)
            }
        })

    # KEY FIGURES (simple pattern)
    kf_set = set()
    for ln in lines:
        found = re.findall(r"Z[A-Z0-9_]{5,}", ln)
        for x in found:
            kf_set.add(x)
    spec["key_figures"] = sorted(kf_set)

    # MOVE_Z_SP blocks
    for m in re.finditer(r"MOVE_Z_SP_(\d+)", text):
        num = m.group(1)
        name = f"MOVE_Z_SP_{num}"
        spec["move_blocks"][name] = extract_block(text, name)

    return spec


# ---------------------------------------------------------
# EXTRACT FORM BLOCK
# ---------------------------------------------------------
def extract_block(text: str, form_name: str):
    pattern = rf"FORM\s+{re.escape(form_name)}\b(.+?)ENDFORM\."
    m = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------
# VARIABLE PARSERS
# ---------------------------------------------------------
def extract_ranges(block: str):
    """
    Returns pairs like [["LS0155","HS0155"], ...]
    """
    ls = re.findall(r"LS(\d+)", block)
    hs = re.findall(r"HS(\d+)", block)
    return [[f"LS{a}", f"HS{b}"] for a, b in zip(ls, hs)]


def extract_singles(block: str):
    """
    Returns single-variable entries: ["LK1234", ...]
    """
    matches = re.findall(r"LSK", block)
    return [f"LK{m}" for m in matches]


# ---------------------------------------------------------
# DOCUMENTATION
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# TEST DATA
# ---------------------------------------------------------
def generate_testdata(spec: dict):
    headers = []
    rows = []

    # headers
    for c in spec["characteristics"]:
        headers.append(c["infoobject"])
    for k in spec["key_figures"]:
        headers.append(k)

    # 5 rows of dummy data
    for i in range(5):
        row = []
        for c in spec["characteristics"]:
            row.append(f"{c['infoobject']}_{i+1}")
        for k in spec["key_figures"]:
            row.append(i + 1)
        rows.append(row)

    return headers, rows


# ---------------------------------------------------------
# MAIN PROCESSOR
# ---------------------------------------------------------
def process_gp_file(path: Path, overrides: dict, out_dir: Path):
    """
    Main pipeline for generating:
      * JSON spec
      * Markdown documentation
      * Test data CSV
    """
    text = _read_text(path)
    spec = parse_gp_text(text, overrides)

    # JSON
    _write_json(spec, out_dir / f"{path.stem}_spec.json")

    # Markdown
    md = generate_doc(spec)
    _write_md(md, out_dir / f"{path.stem}_documentation.md")

    # CSV test data
    headers, rows = generate_testdata(spec)
    _write_csv(rows, headers, out_dir / f"{path.stem}_testdata.csv")
