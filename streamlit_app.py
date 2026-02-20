import streamlit as st
from pathlib import Path
import traceback

st.set_page_config(page_title="agent.py DIAGNOSTIC", layout="wide")
st.title("🔎 agent.py Diagnostic")

agent_path = Path("agent.py")
if not agent_path.exists():
    st.error("agent.py is missing in the repo root. Create it first.")
    st.stop()

# Read agent.py safely (show non-utf8 as replacement chars)
code_text = agent_path.read_text(encoding="utf-8", errors="replace")

st.subheader("First 30 lines of agent.py (for visual check)")
preview = "\n".join(code_text.splitlines()[:30])
st.code(preview, language="python")

st.subheader("Compile check")
try:
    compile(code_text, "agent.py", "exec")
    st.success("✅ agent.py compiles successfully (no syntax errors).")
    st.info("You can now restore the full app that imports agent and runs conversion.")
except SyntaxError as e:
    st.error(f"❌ SyntaxError in agent.py at line {e.lineno}, column {e.offset}: {e.msg}")
    lines = code_text.splitlines()
    bad = lines[e.lineno-1] if 1 <= e.lineno <= len(lines) else ""
    st.write("Problem line:")
    st.code(bad, language="python")
    st.stop()
