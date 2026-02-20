import streamlit as st
import tempfile
from pathlib import Path
import json
import agent
from utils import zip_named_files, extract_zip_to_tmp, iter_files

# ----------------------------
# STREAMLIT SETUP
# ----------------------------
st.set_page_config(page_title="BEx GP Converter", layout="wide")
st.title("🧠 BEx GP Converter")

st.write("""
Upload BEx GP (.txt) files or a ZIP file containing GP files.
The tool will generate:
- JSON specification  
- Markdown documentation  
- Test data CSV  
""")

# ----------------------------
# INPUT MODE
# ----------------------------
mode = st.selectbox("Select input mode:", [
    "Upload GP .txt files",
    "Upload ZIP (folder of GP files)",
    "Local folder path (run locally)"
])

with st.expander("Advanced notes (optional)"):
    notes = st.text_area("Notes for documentation", height=120)

uploads = None
zip_up = None
folder = None

if mode == "Upload GP .txt files":
    uploads = st.file_uploader("Upload GP files", type=["txt"], accept_multiple_files=True)

elif mode == "Upload ZIP (folder of GP files)":
    zip_up = st.file_uploader("Upload ZIP", type=["zip"])

else:
    folder = st.text_input("Enter local folder path", "")

# ----------------------------
# RUN BUTTON
# ----------------------------
if st.button("🚀 Run Conversion", type="primary"):
    # Working directories
    tmp = Path(tempfile.mkdtemp())
    in_dir = tmp / "in"
    out_dir = tmp / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    # Resolve inputs to a list of GP .txt files
    gp_files: list[Path] = []

    if uploads:
        for f in uploads:
            p = in_dir / f.name
            p.write_bytes(f.getvalue())
        gp_files = list(in_dir.glob("*.txt"))

    elif zip_up:
        root = extract_zip_to_tmp(zip_up)
        gp_files = iter_files(root, (".txt",))

    else:
        if not folder:
            st.error("Please enter a local folder path or choose a different mode.")
            st.stop()
        root = Path(folder)
        gp_files = iter_files(root, (".txt",))

    if not gp_files:
        st.error("⚠️ No .txt GP files found.")
        st.stop()

    # Run processing
    bundle = {}
    logs = []

    # Overrides are optional; only used if a char_map_overrides.json is present
    overrides = agent.load_overrides(in_dir if uploads else (root if (zip_up is None and folder) else root if zip_up else in_dir))

    for src in gp_files:
        # Copy each file under in_dir so outputs collect in out_dir
        dst = in_dir / src.name
        try:
            if src.exists():
                dst.write_bytes(src.read_bytes())
        except Exception:
            # If src is already under in_dir (uploads case), ignore
            pass

        # Process with the agent
        agent.process_gp_file(dst, overrides, out_dir)
        logs.append(f"Processed: {src.name}")

    # Collect generated outputs into a ZIP bundle
    for f in out_dir.glob("*"):
        bundle[f.name] = f.read_bytes()

    # Results
    st.success("🎉 Conversion Completed Successfully!")
    st.code("\n".join(logs), language="text")

    st.download_button(
        "📦 Download Results (ZIP)",
        data=zip_named_files(bundle),
        file_name="bex_output.zip",
        mime="application/zip"
    )
