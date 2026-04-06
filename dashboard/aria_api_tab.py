"""API server tab — requires aria-os-export for full functionality."""
import streamlit as st

try:
    import aria_os  # noqa: F401
    _HAS_ARIA_OS = True
except ImportError:
    _HAS_ARIA_OS = False


def render_api_tab():
    st.header("ARIA-OS API Server")
    if not _HAS_ARIA_OS:
        st.warning(
            "aria-os-export not installed. Install with:\n\n"
            "```\npip install -e ../aria-os-export\n```\n\n"
            "This tab requires the ARIA-OS CAD pipeline."
        )
        return

    import json
    import subprocess

    st.subheader("Server Status")
    try:
        import requests
        r = requests.get("http://localhost:8000/api/health", timeout=3)
        if r.ok:
            st.success("API server is running")
            st.json(r.json())
        else:
            st.error(f"Server returned {r.status_code}")
    except Exception:
        st.warning("API server not running. Start with: `uvicorn aria_os.api_server:app`")

    st.subheader("Generate Part")
    desc = st.text_input("Part description", "M10 hex bolt 30mm")
    if st.button("Generate"):
        try:
            import requests
            r = requests.post("http://localhost:8000/api/generate/sync",
                              json={"description": desc}, timeout=120)
            st.json(r.json())
        except Exception as e:
            st.error(str(e))

    st.subheader("Recent Runs")
    try:
        import requests
        r = requests.get("http://localhost:8000/api/runs?limit=10", timeout=3)
        if r.ok:
            runs = r.json().get("runs", [])
            if runs:
                import pandas as pd
                st.dataframe(pd.DataFrame(runs), use_container_width=True)
            else:
                st.info("No runs yet.")
    except Exception:
        st.info("Start the API server to see run history.")
