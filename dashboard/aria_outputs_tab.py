"""Outputs browser tab — works standalone, browses outputs/ directory."""
import os
from datetime import datetime
from pathlib import Path
import streamlit as st


_FILE_TYPES = {
    ".step": "STEP", ".stp": "STEP", ".stl": "STL", ".svg": "Drawing",
    ".ghx": "Grasshopper", ".dxf": "DXF", ".py": "Script", ".json": "JSON",
    ".png": "Image", ".md": "Markdown",
}


def render_outputs_tab():
    st.header("Pipeline Outputs Browser")
    out_dir = Path(__file__).resolve().parent.parent / "outputs"
    if not out_dir.exists():
        st.info("No `outputs/` directory found.")
        return

    # Collect all files
    files = []
    for p in out_dir.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            files.append({
                "name": p.name,
                "path": str(p.relative_to(out_dir)),
                "type": _FILE_TYPES.get(p.suffix.lower(), "Other"),
                "size_kb": round(p.stat().st_size / 1024, 1),
                "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })

    if not files:
        st.info("No output files yet.")
        return

    # Metrics
    cols = st.columns(4)
    cols[0].metric("Total Files", len(files))
    cols[1].metric("STEP Files", sum(1 for f in files if f["type"] == "STEP"))
    cols[2].metric("STL Files", sum(1 for f in files if f["type"] == "STL"))
    total_mb = sum(f["size_kb"] for f in files) / 1024
    cols[3].metric("Total Size", f"{total_mb:.1f} MB")

    # Filter
    types = sorted(set(f["type"] for f in files))
    sel_type = st.selectbox("Filter by type", ["All"] + types)
    if sel_type != "All":
        files = [f for f in files if f["type"] == sel_type]

    import pandas as pd
    df = pd.DataFrame(files).sort_values("modified", ascending=False)
    st.dataframe(df, use_container_width=True)
