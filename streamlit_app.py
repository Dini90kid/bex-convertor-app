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
    
    # Create a temporary working area
    tmp = Path(tempfile.mkdtemp())
    in_dir = tmp / "in"
    out_dir = tmp / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    gp_files = []

    # ----------------------------
    # LOAD INPUT FILES
    # ----------------------------
    if uploads:
        for f in uploads:
            p = in_dir / f.name
            p.write_bytes(f.getvalue())
        gp_files = list(in_dir.glob("*.txt"))

    elif zip_up:
        root = extract_zip_to_tmp(zip_up)
        gp_files = iter_files(root, (".txt",))

    else:
        root = Path(folder)
        gp_files = iter_files(root, (".txt",))

    if not gp_files:
        st.error("⚠️ No .txt GP files found.")
        st.stop()

    # ----------------------------
    # PROCESS FILES
    # ----------------------------
    bundle = {}
    logs = []

    overrides = agent.load_overrides(in_dir)

    for f in gp_files:
        dst = in_dir / f.name

        # Copy file (if needed)
        try:
            if f.exists():
                dst.write_bytes(f.read_bytes())
        except:
            pass

        # Run the agent to generate output files
        agent.process_gp_file(dst, overrides, out_dir)
        logs.append(f"Processed: {f.name}")

    # Collect all generated output
    for file in out_dir.glob("*"):
        bundle[file.name] = file.read_bytes()

    # ----------------------------
    # RESULTS
    # ----------------------------
    st.success("🎉 Conversion Completed Successfully!")
    st.code("\n".join(logs))

    st.download_button(
        "📦 Download Results (ZIP)",
        data=zip_named_files(bundle),
        file_name="bex_output.zip",
        mime="application/zip"
    )
