from pathlib import Path
import io, zipfile, os
import tempfile

def zip_named_files(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    buf.seek(0)
    return buf.read()

def extract_zip_to_tmp(uploaded_zip):
    tmp = Path(tempfile.mkdtemp())
    zf = zipfile.ZipFile(io.BytesIO(uploaded_zip.getvalue()))
    zf.extractall(tmp)
    return tmp

def iter_files(root: Path, extensions: tuple[str, ...]):
    exts = tuple(e.lower() for e in extensions)
    results = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if Path(fn).suffix.lower() in exts:
                results.append(Path(dirpath) / fn)
    return results
