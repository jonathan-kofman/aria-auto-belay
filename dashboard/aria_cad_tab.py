"""CAD pipeline tab — requires aria-os-export for full functionality."""
import streamlit as st

try:
    from aria_os.dashboard_bridge import (
        get_parts_library,
        get_material_study_results,
        get_cem_constants,
        get_assembly_status,
        get_manufacturing_readiness,
    )
    _HAS_ARIA_OS = True
except ImportError:
    _HAS_ARIA_OS = False


def render_cad_tab():
    st.header("ARIA-OS: CAD & Manufacturing")
    if not _HAS_ARIA_OS:
        st.warning(
            "aria-os-export not installed. Install with:\n\n"
            "```\npip install -e ../aria-os-export\n```\n\n"
            "This tab requires the ARIA-OS CAD pipeline."
        )
        return

    st.subheader("Parts Library")
    parts = get_parts_library()
    if parts:
        import pandas as pd
        df = pd.DataFrame([{
            "Part": p["name"][:60],
            "BBox (mm)": f"{(p.get('bbox_mm') or {}).get('x', 0):.0f}x{(p.get('bbox_mm') or {}).get('y', 0):.0f}x{(p.get('bbox_mm') or {}).get('z', 0):.0f}",
            "SF": p.get("sf_value", "N/A"),
            "STEP": "OK" if p.get("step_path") else "MISSING",
        } for p in parts])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No parts generated yet. Run `python run_aria_os.py ...` to generate.")

    st.subheader("Material Study")
    mat = get_material_study_results()
    if mat:
        for name, r in list(mat.items())[:50]:
            c = st.columns(3)
            c[0].write(name[:50]); c[1].write(r.get("recommendation", "N/A"))
            sf = r.get("recommendation_sf"); c[2].write(f"{sf:.2f}x" if isinstance(sf, (int, float)) else "N/A")
    else:
        st.info("No material study results.")

    st.subheader("Assembly")
    assy = get_assembly_status()
    if assy:
        st.metric("Parts in Assembly", assy.get("part_count", 0))
    else:
        st.info("No assembly config found.")
