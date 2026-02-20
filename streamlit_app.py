import streamlit as st
import json, tempfile
from pathlib import Path
import agent
from utils import zip_named_files, extract_zip_to_tmp, iter_files, build_pyspark_from_spec

st.set_page_config(page_title="BEx GP Converter", layout="wide")
st.title("🧠 BEx GP Converter")

mode = st.selectbox("Input mode", [
    "Upload GP .txt",
    "Upload ZIP (GP files)",
    "Local folder path"
])

with st.expander("Advanced notes (optional)"):
    notes = st.text_area("Notes", "")

uploads = None
zip_up = None
folder = None

if mode == "Upload GP .txt":
    uploads = st.file_uploader("Upload GP files", type=["txt"], accept_multiple_files=True)
elif mode == "Upload ZIP (GP files)":
    zip_up = st.file_uploader("Upload ZIP", type=["zip"])
else:
    folder = st.text_input("Local folder path", "")

if st.button("Run"):
    tmp = Path(tempfile.mkdtemp())
    in_dir = tmp / "in"
    out_dir = tmp / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    gp_files = []
    if uploads:
        for f in uploads:
            (in_dir / f.name).write_bytes(f.getvalue())
        gp_files = list(in_dir.glob("*.txt"))
    elif zip_up:
        root = extract_zip_to_tmp(zip_up)
        gp_files = iter_files(root, (".txt",))
    else:
        gp_files = iter_files(Path(folder), (".txt",))

    bundle = {}
    logs = []

    overrides = agent.load_overrides(in_dir)

    for f in gp_files:
        dst = in_dir / f.name
        if not f.exists():
            pass
        else:
            try:
                dst.write_bytes(f.read_bytes())
            except:
                pass

        agent.process_gp_file(dst, overrides, out_dir)
        logs.append(f"Processed {f.name}")

        spec_files = list(out_dir.glob("*_spec.json"))
        if spec_files:
            spec = json.loads(spec_files[0].read_text())
            pys = build_pyspark_from_spec(spec, notes)
            bundle[f"{spec['query_name']}_spark.py"] = pys.encode()

    for f in out_dir.glob("*"):
        bundle[f.name] = f.read_bytes()

    st.success("Done")
    st.code("\n".join(logs))
    st.download_button("Download ZIP", data=zip_named_files(bundle),
                       file_name="bex_output.zip", mime="application/zip")
``
