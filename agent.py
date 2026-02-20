# ===============================
# agent.py – Clean BEx GP Parser
# ===============================

from pathlib import Path
import re
import json
import csv

# ---------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------

def _read_text(path: Path) -> str:
    """Reads text from a file with UTF‑8 fallback."""
    try:
        return path.read_text(encoding="utf-8")
    except:
        return path.read_text(encoding="latin-1", errors="ignore")


def _write_json(data, out_path: Path):
    out_path.write_text(json(rows)    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------
# OVERRIDES LOADER
# ---------------------------------------------------------

def load_overrides(folder: Path):
    """Loads overrides JSON if present."""
    ov = folder / "char_map_overrides.json"
    if ov.exists():
        try:
            return json.loads(ov.read_text())
        except:
            return {}
    return {}


# ---------------------------------------------------------
# CORE PARSER
# ---------------------------------------------------------

def parse_gp_text(txt: str, overrides: dict):
    """
    Parse a BEx generated program GP text.
    Extract:
      - Query metadata
      - InfoProvider / Cube
      - Characteristics
      - Variables
      - Key Figures
      - MOVE_Z_SP logic
    """

    lines = txt.splitlines()

    # -----------------------------
    # 1) METADATA
    # -----------------------------
    metadata = {}

    rep = re.search(r"REPORT:\s*(\S+)", txt)
    if rep:
        metadata["report"] = rep.group(1)

    cube = re.search(r"INFOCUBE\.*:\s*(\S+)", txt)
    if cube:
        metadata["infocube"] = cube.group(1)

    # -----------------------------
    # 2) CHARACTERISTICS & VARIABLES
    # -----------------------------

    chars = []
    variables = {}

    # Pattern: FORM A_S_XXXX (Single/Range Vars)
    for m in re.finditer(r"FORM\s+A_S_(\d+)", txt):
        tech_id = m.group(1)
        block = extract_form_block(txt, f"A_S_{tech_id}")
        ranges = extract_ranges(block)
        singles = extract_singles(block)

        chars.append({
            "tech_id": tech_id,
            "infoobject": overrides.get(tech_id, f"CH_{tech_id}"),
            "variables": {
                "ranges": ranges,
                "single": singles
            }
        })

    # Pattern: FORM A_K_XXXX (Key variances)
    for m in re.finditer(r"FORM\s+A_K_(\d+)", txt):
        tech_id = m.group(1)
        block = extract_form_block(txt, f"A_K_{tech_id}")
        singles = extract_singles(block)
        chars.append({
            "tech_id": tech_id,
            "infoobject": overrides.get(tech_id, f"CH_{tech_id}"),
            "variables": {
                "ranges": [],
                "single": singles
            }
        })

    # -----------------------------
    # 3) KEY FIGURES
    # -----------------------------
    kf = set()
    for line in lines:
        if "SUM" in line or "Z____" in line:
            m = re.findall(r"Z[_A-Z0-9]{10,}", line)
            for x in m:
                kf.add(x)

    key_figures = sorted(kf)

    # -----------------------------
    # 4) MOVE_Z_SP transformations
    # -----------------------------
    move_blocks = {}
    for m in re.finditer(r"MOVE_Z_SP_(\d+)", txt):
        num = m.group(1)
        move_blocks[f"MOVE_Z_SP_{num}"] = extract_form_block(txt, f"MOVE_Z_SP_{num}")

    # -----------------------------
    # FINAL SPEC
    # -----------------------------
    spec = {
        "query_name": metadata.get("report", "UNKNOWN"),
        "infocube": metadata.get("infocube", "UNKNOWN"),
        "characteristics": chars,
        "key_figures": key_figures,
        "move_blocks": move_blocks
    }

    return spec


# ---------------------------------------------------------
# FORM BLOCK EXTRACTOR
# ---------------------------------------------------------

def extract_form_block(txt: str, form_name: str):
    """
    Extracts text from:
      FORM <form_name> 
      to
      ENDFORM.
    """
    pattern = (
        rf"FORM\s+{re.escape(form_name)}\b(.+?)ENDFORM\."
    )
    m = re.search(pattern, txt, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------
# VARIABLE RANGE / SINGLE EXTRACTION
# ---------------------------------------------------------

def extract_ranges(block: str):
    """Extract RANGES: LSxxxx HSxxxx pairs."""
    ranges = []
    ls = re.findall(r"LS(\d+)", block)
    hs = re.findall(r"HS(\d+)", block)
    # pair them safely
    for a, b in zip(ls, hs):
        ranges.append([f"LS{a}", f"HS{b}"])
    return ranges


def extract_singles(block: str):
    """Extract single selections LKxxxx or LSxxxx."""
    singles = []
    for m in re.findall(r"LSK", block):
        singles.append(f"LK{m}")
    return singles


# ---------------------------------------------------------
# DOCUMENTATION GENERATOR
# ---------------------------------------------------------

def generate_markdown(spec: dict, notes: str = ""):
    md = []
    md.append(f"# Query: {spec.get('query_name')}")
    md.append("")
    md.append(f"**InfoProvider:** {spec.get('infocube')}")
    md.append("")

    md.append("## Characteristics")
    for c in spec["characteristics"]:
        md.append(f"- **{c['infoobject']}** (Tech ID: {c['tech_id']})")
        md.append(f"  - Ranges: {c['variables']['ranges']}")
        md.append(f"  - Single: {c['variables']['single']}")

    md.append("")
    md.append("## Key Figures")
    for k in spec["key_figures"]:
        md.append(f"- {k}")

    md.append("")
    md.append("## MOVE_Z_SP Blocks")
    for k, block in spec["move_blocks"].items():
        md.append(f"### {k}")
        md.append("```")
        md.append(block)
        md.append("```")

    if notes:
        md.append("")
        md.append("## Notes")
        md.append(notes)

    return "\n".join(md)


# ---------------------------------------------------------
# TEST DATA GENERATOR
# ---------------------------------------------------------

def generate_testdata(spec: dict):
    """
    Simple test-data generator:
      - For each characteristic → sample value
      - For each KF → dummy numeric
    Generates 5 rows.
    """
    rows = []
    headers = []

    # Characteristics
    for c in spec["characteristics"]:
        headers.append(c["infoobject"])

    # KFs
    for k in spec["key_figures"]:
        headers.append(k)

    for i in range(5):
        row = []
        # values
        for c in spec["characteristics"]:
            row.append(f"{c['infoobject']}_{i+1}")
        for k in spec["key_figures"]:
            row.append(i + 1)
        rows.append(row)

    return headers, rows


# ---------------------------------------------------------
# MAIN ENTRY — CALLED FROM STREAMLIT
# ---------------------------------------------------------

def process_gp_file(path: Path, overrides: dict, out_dir: Path):
    """
    Full workflow:
      1. Read GP file
      2. Parse spec
      3. Write JSON spec
      4. Write Markdown documentation
      5. Write test data CSV
    """

    txt = _read_text(path)
    spec = parse_gp_text(txt, overrides)

    # Write JSON
    spec_path = out_dir / f"{path.stem}_spec.json"
    _write_json(spec, spec_path)

    # Write Markdown
    md = generate_markdown(spec)
    md_path = out_dir / f"{path.stem}_documentation.md"
    _write_md(md, md_path)

    # Write test data
    headers, rows = generate_testdata(spec)
    csv_path = out_dir / f"{path.stem}_testdata.csv"
    _write_csv(rows, headers, csv_path)

    return spec


def _write_md(text, out_path: Path):
    out_path.write_text(text, encoding="utf-8")


def _write_csv(rows, headers, out_path: Path):
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
