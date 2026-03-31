"""
Rhino Compute runner for aria_cam_collar.
Usage:  python "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/grasshopper/aria_cam_collar/aria_cam_collar_rhinoscript.py"
        RHINO_COMPUTE_URL=http://your-server:6500 python "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/grasshopper/aria_cam_collar/aria_cam_collar_rhinoscript.py"
See docs/rhino_compute_setup.md for setup.
"""
import json, os, sys
from pathlib import Path

SCRIPT_PATH = Path("C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/grasshopper/aria_cam_collar/aria_cam_collar_rhinoscript.py")
STEP_PATH   = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/step/aria_cam_collar.step"
STL_PATH    = "C:/Users/jonko/Downloads/aria-auto-belay/outputs/cad/stl/aria_cam_collar.stl"
PART_NAME   = "aria_cam_collar"
COMPUTE_URL = os.environ.get("RHINO_COMPUTE_URL", "http://localhost:6500")


def _run():
    import urllib.request
    script_code = SCRIPT_PATH.read_text(encoding='utf-8')
    payload = json.dumps({'script': script_code}).encode('utf-8')
    req = urllib.request.Request(
        f'{COMPUTE_URL}/grasshopper',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        print(f'[RHINO-COMPUTE] Unavailable: {e}', file=sys.stderr)
        print(f'[RHINO-COMPUTE] Artifacts written. Run manually: aria_cam_collar_rhinoscript.py', file=sys.stderr)
        sys.exit(0)  # Non-fatal; pipeline continues
    for line in result.get('stdout', '').splitlines():
        print(line)
    rc = result.get('returncode', 0)
    if rc != 0:
        err = result.get('stderr', '')[:300]
        print(f'[RHINO-COMPUTE] Script failed (rc={rc}): {err}', file=sys.stderr)
        sys.exit(rc)


if __name__ == "__main__":
    _run()
