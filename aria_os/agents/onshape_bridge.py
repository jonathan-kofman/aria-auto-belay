"""Onshape API bridge — creates parametric parts directly in Onshape from ARIA-OS.

This is the MecAgent-equivalent capability: natural language → live parametric
CAD model in the user's Onshape workspace, with editable features.

Authentication: Set ONSHAPE_ACCESS_KEY and ONSHAPE_SECRET_KEY env vars.
Generate keys at: https://cad.onshape.com/appstore/dev-portal

Usage:
    from aria_os.agents.onshape_bridge import OnshapeBridge
    bridge = OnshapeBridge()
    url = bridge.create_part("My Bracket", spec={
        "width_mm": 100, "height_mm": 60, "thickness_mm": 8,
        "n_bolts": 4, "bolt_dia_mm": 6,
    })
    # Returns: https://cad.onshape.com/documents/...  (live editable part)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

_BASE_URL = "https://cad.onshape.com/api/v6"


def _load_env_key(key: str) -> str:
    """Read a key from env vars, falling back to .env file."""
    val = os.environ.get(key, "")
    if val:
        return val
    # Try .env file
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return ""


class OnshapeAuth:
    """Onshape API key authentication."""

    def __init__(self):
        self.access_key = _load_env_key("ONSHAPE_ACCESS_KEY")
        self.secret_key = _load_env_key("ONSHAPE_SECRET_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.access_key and self.secret_key)

    def make_headers(self, method: str = "", path: str = "", query: str = "",
                     content_type: str = "application/json") -> dict[str, str]:
        """Build authenticated headers using Basic auth (simpler, reliable)."""
        basic = base64.b64encode(
            f"{self.access_key}:{self.secret_key}".encode("utf-8")
        ).decode("utf-8")
        return {
            "Content-Type": content_type,
            "Accept": "application/json",
            "Authorization": f"Basic {basic}",
        }


# ---------------------------------------------------------------------------
# API Client
# ---------------------------------------------------------------------------

class OnshapeClient:
    """Low-level Onshape REST API client."""

    def __init__(self, auth: OnshapeAuth | None = None):
        self.auth = auth or OnshapeAuth()

    def _request(self, method: str, path: str, data: dict | None = None,
                 query: str = "", content_type: str = "application/json",
                 raw_body: bytes | None = None) -> dict:
        """Make an authenticated API request."""
        url = f"{_BASE_URL}{path}"
        if query:
            url += f"?{query}"

        headers = self.auth.make_headers(method, path, query, content_type=content_type)
        if raw_body is not None:
            body = raw_body
        else:
            body = json.dumps(data).encode() if data else None

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Onshape API {exc.code}: {error_body}") from exc

    def get(self, path: str, **kw) -> dict:
        return self._request("GET", path, **kw)

    def post(self, path: str, data: dict, **kw) -> dict:
        return self._request("POST", path, data=data, **kw)

    def delete(self, path: str, **kw) -> dict:
        return self._request("DELETE", path, **kw)

    def upload_blob(self, did: str, wid: str, file_path: str,
                    filename: str = "") -> dict:
        """Upload a file (STEP, etc.) as a blob element to an Onshape document.
        Uses multipart/form-data upload endpoint.
        Returns the translation status / element info."""
        from pathlib import Path as _P
        fp = _P(file_path)
        filename = filename or fp.name

        # Build multipart/form-data body
        boundary = f"----OnshapeBoundary{uuid.uuid4().hex[:16]}"
        body_parts = []

        # File part
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode()
        )
        body_parts.append(b"Content-Type: application/octet-stream")
        body_parts.append(b"")
        body_parts.append(fp.read_bytes())

        # Flatten flag
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(b'Content-Disposition: form-data; name="flattenAssemblies"')
        body_parts.append(b"")
        body_parts.append(b"false")

        # Allow faulty parts
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(b'Content-Disposition: form-data; name="allowFaultyParts"')
        body_parts.append(b"")
        body_parts.append(b"true")

        body_parts.append(f"--{boundary}--".encode())

        raw_body = b"\r\n".join(body_parts)
        content_type = f"multipart/form-data; boundary={boundary}"

        path = f"/blobelements/d/{did}/w/{wid}"
        return self._request("POST", path, content_type=content_type,
                             raw_body=raw_body)


# ---------------------------------------------------------------------------
# Feature Builders — convert ARIA specs to Onshape feature JSON
# ---------------------------------------------------------------------------

def _make_sketch_circle(x_m: float, y_m: float, radius_m: float, entity_id: str = "c1") -> dict:
    """Create a circle sketch entity."""
    return {
        "btType": "BTMSketchCurve-4",
        "centerId": f"{entity_id}.center",
        "entityId": entity_id,
        "geometry": {
            "btType": "BTCurveGeometryCircle-115",
            "radius": radius_m,
            "xCenter": x_m,
            "yCenter": y_m,
            "clockwise": False,
        },
    }


def _make_sketch_rect(cx_m: float, cy_m: float, w_m: float, h_m: float) -> list[dict]:
    """Create a rectangle as 4 sketch line entities."""
    x1, y1 = cx_m - w_m / 2, cy_m - h_m / 2
    x2, y2 = cx_m + w_m / 2, cy_m + h_m / 2
    lines = []
    pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    for i in range(4):
        p1 = pts[i]
        p2 = pts[(i + 1) % 4]
        lines.append({
            "btType": "BTMSketchCurve-4",
            "entityId": f"rect_line_{i}",
            "geometry": {
                "btType": "BTCurveGeometryLine-117",
                "pntX": p1[0], "pntY": p1[1],
                "dirX": p2[0] - p1[0], "dirY": p2[1] - p1[1],
            },
            "startParam": 0.0,
            "endParam": 1.0,
        })
    return lines


def _make_sketch_feature(name: str, plane: str, entities: list[dict]) -> dict:
    """Wrap sketch entities in a sketch feature definition."""
    # Map plane name to Onshape query string
    plane_queries = {
        "top": 'query=qCreatedBy(makeId("Top"), EntityType.FACE);',
        "front": 'query=qCreatedBy(makeId("Front"), EntityType.FACE);',
        "right": 'query=qCreatedBy(makeId("Right"), EntityType.FACE);',
    }
    return {
        "btType": "BTFeatureDefinitionCall-1406",
        "feature": {
            "btType": "BTMSketch-151",
            "featureType": "newSketch",
            "name": name,
            "suppressed": False,
            "parameters": [
                {
                    "btType": "BTMParameterQueryList-148",
                    "parameterId": "sketchPlane",
                    "queries": [{
                        "btType": "BTMIndividualQuery-138",
                        "queryStatement": None,
                        "queryString": plane_queries.get(plane, plane_queries["top"]),
                    }],
                },
            ],
            "entities": entities,
            "constraints": [],
        },
    }


def _make_extrude_feature(name: str, sketch_id: str, depth_m: float,
                           operation: str = "NEW") -> dict:
    """Create an extrude feature definition."""
    # operation: "NEW", "ADD", "REMOVE", "INTERSECT"
    op_map = {"NEW": "NEW", "ADD": "ADD", "REMOVE": "REMOVE", "CUT": "REMOVE"}
    return {
        "btType": "BTFeatureDefinitionCall-1406",
        "feature": {
            "btType": "BTMFeature-134",
            "featureType": "extrude",
            "name": name,
            "suppressed": False,
            "parameters": [
                {
                    "btType": "BTMParameterEnum-145",
                    "parameterId": "bodyType",
                    "enumName": "ExtendedToolBodyType",
                    "value": "SOLID",
                },
                {
                    "btType": "BTMParameterEnum-145",
                    "parameterId": "operationType",
                    "enumName": "NewBodyOperationType",
                    "value": op_map.get(operation, "NEW"),
                },
                {
                    "btType": "BTMParameterQueryList-148",
                    "parameterId": "entities",
                    "queries": [{
                        "btType": "BTMIndividualSketchRegionQuery-140",
                        "featureId": sketch_id,
                    }],
                },
                {
                    "btType": "BTMParameterQuantity-147",
                    "parameterId": "depth",
                    "expression": f"{depth_m} m",
                    "isInteger": False,
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# High-Level Bridge
# ---------------------------------------------------------------------------

class OnshapeBridge:
    """
    Creates live parametric parts in Onshape from ARIA-OS specs.

    Usage:
        bridge = OnshapeBridge()
        result = bridge.create_part("My Bracket", spec={...})
        print(result["url"])  # Opens in browser as editable Onshape part
    """

    def __init__(self):
        self.client = OnshapeClient()
        self.auth = self.client.auth

    @property
    def is_available(self) -> bool:
        return self.auth.is_configured

    def create_document(self, name: str) -> dict:
        """Create a new Onshape document. Returns {documentId, workspaceId, elementId}."""
        result = self.client.post("/documents", data={
            "name": name,
            "isPublic": False,
        })
        did = result["id"]
        # Get the default workspace
        wid = result["defaultWorkspace"]["id"]
        # Get the part studio element
        elements = self.client.get(f"/documents/d/{did}/w/{wid}/elements")
        eid = None
        for el in elements:
            if "part" in el.get("type", "").lower() and "studio" in el.get("type", "").lower():
                eid = el["id"]
                break
        if not eid:
            raise RuntimeError("No Part Studio found in new document")

        return {
            "documentId": did,
            "workspaceId": wid,
            "elementId": eid,
            "url": f"https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}",
        }

    def create_drawing(self, did: str, wid: str, eid: str, name: str = "Drawing") -> dict:
        """Create an Onshape Drawing element linked to the part studio.
        Returns the drawing element ID and URL."""
        try:
            # Create a new drawing element in the document
            result = self.client.post(
                f"/documents/d/{did}/w/{wid}/elements",
                data={
                    "name": name,
                    "elementType": "DRAWING",
                },
            )
            drawing_eid = result.get("id", "")
            url = f"https://cad.onshape.com/documents/{did}/w/{wid}/e/{drawing_eid}"
            return {"elementId": drawing_eid, "url": url}
        except Exception as exc:
            return {"error": str(exc)}

    def upload_step(self, name: str, step_path: str) -> dict[str, Any]:
        """Upload a STEP file to a NEW Onshape document.
        Returns dict with url, documentId, translationId."""
        result = self.client.post("/documents", data={
            "name": name,
            "isPublic": False,
        })
        did = result["id"]
        wid = result["defaultWorkspace"]["id"]

        # Upload STEP as blob element
        upload_result = self.client.upload_blob(did, wid, step_path)
        eid = upload_result.get("id", "")
        tid = upload_result.get("translationId", "")

        url = f"https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}"
        return {
            "status": "ok",
            "url": url,
            "documentId": did,
            "workspaceId": wid,
            "elementId": eid,
            "translationId": tid,
        }

    def verify_upload(self, did: str, wid: str, expected_bbox: dict | None = None,
                      max_wait: int = 30) -> dict[str, Any]:
        """Verify a STEP upload translated correctly.

        Polls until a *translated* Part Studio appears (name != "Part Studio 1"),
        then checks it has ≥1 solid part. Returns the correct Part Studio URL.

        Returns {verified, parts, bbox, issues, part_studio_eid, url}
        """
        import time as _time
        result = {"verified": False, "parts": 0, "bbox": {},
                  "issues": [], "part_studio_eid": "", "url": ""}

        # Poll for the translated Part Studio (Onshape creates it asynchronously)
        # The default doc has "Part Studio 1" (empty) — we want the translated one
        ps_eid = None
        for attempt in range(max_wait // 3):
            try:
                elements = self.client.get(f"/documents/d/{did}/w/{wid}/elements")
                for el in elements:
                    el_type = el.get("type", "")
                    el_name = el.get("name", "")
                    # Translated Part Studio has a real name (not "Part Studio 1")
                    if "Part Studio" in el_type and el_name != "Part Studio 1":
                        ps_eid = el["id"]
                        break
                if ps_eid:
                    break
            except Exception:
                pass
            _time.sleep(3)

        if not ps_eid:
            # Translation may still be running — check if any Part Studio exists
            try:
                elements = self.client.get(f"/documents/d/{did}/w/{wid}/elements")
                for el in elements:
                    if "Part Studio" in el.get("type", ""):
                        ps_eid = el["id"]
                        break
            except Exception:
                pass

        if not ps_eid:
            result["issues"].append("No Part Studio found after translation")
            return result

        # Update URL to point at the Part Studio (not the blob)
        result["url"] = f"https://cad.onshape.com/documents/{did}/w/{wid}/e/{ps_eid}"
        result["part_studio_eid"] = ps_eid

        # Get parts list
        try:
            parts = self.client.get(f"/parts/d/{did}/w/{wid}/e/{ps_eid}")
            if isinstance(parts, list):
                result["parts"] = len(parts)
            else:
                result["parts"] = 1
        except Exception as exc:
            result["issues"].append(f"Parts query failed: {exc}")

        if result["parts"] == 0:
            result["issues"].append("Translation produced 0 parts")
            return result

        # Get bounding box (may not be available for all translations)
        try:
            bb_resp = self.client.get(
                f"/partstudios/d/{did}/w/{wid}/e/{ps_eid}/boundingboxes")
            low = bb_resp.get("lowPoint", {})
            high = bb_resp.get("highPoint", {})
            if low and high:
                result["bbox"] = {
                    "x_mm": round((high.get("x", 0) - low.get("x", 0)) * 1000, 1),
                    "y_mm": round((high.get("y", 0) - low.get("y", 0)) * 1000, 1),
                    "z_mm": round((high.get("z", 0) - low.get("z", 0)) * 1000, 1),
                }
        except Exception:
            pass  # bbox query not always available — don't fail verification

        # Compare bbox if both available
        if expected_bbox and result["bbox"]:
            eb_vals = sorted(expected_bbox.values())
            ob_vals = sorted(result["bbox"].values())
            if len(eb_vals) >= 3 and len(ob_vals) >= 3:
                for ev, ov in zip(eb_vals, ob_vals):
                    if ev > 0 and abs(ov - ev) / ev > 0.25:
                        result["issues"].append(
                            f"Bbox mismatch: expected ~{ev:.1f}mm, got {ov:.1f}mm")

        result["verified"] = result["parts"] > 0 and len(result["issues"]) == 0
        return result

    def verify_geometry(self, step_path: str, spec: dict, goal: str = "",
                        did: str = "", wid: str = "", ps_eid: str = "") -> dict[str, Any]:
        """Deep verification: inspect local STEP geometry and compare against goal spec.

        Checks: bbox, bore, bolt holes, bolt circle, solid count.
        Optionally fetches Onshape shaded view and saves to screenshots/.

        Returns {verified, checks: [{name, expected, actual, passed}], screenshot, issues}
        """
        import math
        result = {"verified": True, "checks": [], "issues": [], "screenshot": ""}

        def _check(name, expected, actual, passed):
            result["checks"].append({
                "name": name, "expected": str(expected),
                "actual": str(actual), "passed": passed,
            })
            if not passed:
                result["verified"] = False
                result["issues"].append(f"{name}: expected {expected}, got {actual}")

        # Load STEP
        try:
            import cadquery as _cq
            shape = _cq.importers.importStep(step_path)
            bb = shape.val().BoundingBox()
        except Exception as exc:
            result["verified"] = False
            result["issues"].append(f"STEP load failed: {exc}")
            return result

        # Check solid count
        n_solids = len(shape.val().Solids())
        _check("solids", ">=1", n_solids, n_solids >= 1)

        # Check bbox against spec
        bbox = {"x": round(bb.xlen, 1), "y": round(bb.ylen, 1), "z": round(bb.zlen, 1)}
        od = spec.get("od_mm")
        if od:
            closest_axis = min(bbox.values(), key=lambda v: abs(v - float(od)))
            _check("OD", f"~{od}mm", f"{closest_axis}mm",
                   abs(closest_axis - float(od)) / float(od) < 0.25)

        thickness = spec.get("thickness_mm") or spec.get("height_mm")
        if thickness:
            min_axis = min(bbox.values())
            _check("thickness", f"~{thickness}mm", f"{min_axis}mm",
                   min_axis <= float(thickness) * 3)

        # Extract circular features from STEP edges
        circles = []
        for edge in shape.val().Edges():
            try:
                if hasattr(edge, 'geomType') and edge.geomType() == 'CIRCLE':
                    center = edge.Center()
                    r = edge.radius()
                    circles.append({
                        "r": round(r, 2),
                        "cx": round(center.x, 1),
                        "cy": round(center.y, 1),
                    })
            except Exception:
                pass

        radii = sorted(set(c["r"] for c in circles))

        # Check bore
        bore_mm = spec.get("bore_mm")
        if bore_mm:
            bore_r = float(bore_mm) / 2
            bore_found = any(abs(r - bore_r) < max(1.0, bore_r * 0.1) for r in radii)
            _check("bore", f"{bore_mm}mm (r={bore_r}mm)",
                   f"{'found' if bore_found else 'MISSING'} (radii: {radii})", bore_found)

        # Check bolt holes
        n_bolts = spec.get("n_bolts")
        bolt_dia = spec.get("bolt_dia_mm")
        if n_bolts and bolt_dia:
            bolt_r = float(bolt_dia) / 2
            bolt_circles = [c for c in circles if abs(c["r"] - bolt_r) < max(0.5, bolt_r * 0.2)]
            bolt_positions = set((c["cx"], c["cy"]) for c in bolt_circles)
            _check("bolt_holes", f"{n_bolts}x M{bolt_dia} (r={bolt_r}mm)",
                   f"{len(bolt_positions)} holes found", len(bolt_positions) >= int(n_bolts))

            # Check bolt circle radius
            bcr = spec.get("bolt_circle_r_mm")
            if bcr and bolt_positions:
                dists = [math.sqrt(p[0]**2 + p[1]**2) for p in bolt_positions]
                avg_dist = sum(dists) / len(dists)
                _check("bolt_circle_r", f"~{bcr}mm", f"{avg_dist:.1f}mm",
                       abs(avg_dist - float(bcr)) / float(bcr) < 0.25)

        # Fetch Onshape shaded view if we have document IDs
        if did and wid and ps_eid:
            try:
                url = (f"{_BASE_URL}/partstudios/d/{did}/w/{wid}/e/{ps_eid}"
                       f"/shadedviews")
                params = "outputHeight=600&outputWidth=800&pixelSize=0.0001"
                headers = self.client.auth.make_headers(
                    "GET",
                    f"/partstudios/d/{did}/w/{wid}/e/{ps_eid}/shadedviews",
                    params)
                req = urllib.request.Request(f"{url}?{params}", headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                    images = data.get("images", [])
                    if images:
                        import base64 as _b64
                        img_bytes = _b64.b64decode(images[0])
                        ss_dir = Path(step_path).parent.parent.parent / "screenshots"
                        ss_dir.mkdir(parents=True, exist_ok=True)
                        part_slug = Path(step_path).stem
                        ss_path = ss_dir / f"onshape_{part_slug}.png"
                        ss_path.write_bytes(img_bytes)
                        result["screenshot"] = str(ss_path)
            except Exception:
                pass  # screenshot is optional

        return result

    def add_feature(self, did: str, wid: str, eid: str, feature: dict) -> dict:
        """Add a feature to a part studio."""
        path = f"/partstudios/d/{did}/w/{wid}/e/{eid}/features"
        return self.client.post(path, data=feature)

    def create_part(self, name: str, spec: dict[str, Any],
                    goal: str = "", step_path: str = "") -> dict[str, Any]:
        """
        Create a part in Onshape.

        Primary path: upload STEP file (100% geometry fidelity).
        Fallback: build parametric features from spec.

        Returns dict with: url, documentId, features_added, errors
        """
        if not self.is_available:
            return {
                "status": "error",
                "error": "Onshape API keys not configured. Set ONSHAPE_ACCESS_KEY and ONSHAPE_SECRET_KEY.",
                "setup_url": "https://cad.onshape.com/appstore/dev-portal",
            }

        result = {
            "status": "ok",
            "url": "",
            "documentId": "",
            "features_added": 0,
            "errors": [],
        }

        # PRIMARY: Upload STEP file (exact geometry, no approximation)
        if step_path and Path(step_path).exists():
            try:
                print(f"  [Onshape] Uploading STEP: {Path(step_path).name}")
                upload = self.upload_step(name, step_path)
                result["url"] = upload["url"]
                result["documentId"] = upload["documentId"]
                result["features_added"] = 1
                result["method"] = "step_upload"
                print(f"  [Onshape] STEP uploaded: {upload['url']}")

                # Verify: poll until translated, check parts + bbox
                did = upload["documentId"]
                wid = upload["workspaceId"]
                # Get expected bbox from local STEP
                expected_bbox = spec.get("_expected_bbox")
                if not expected_bbox:
                    try:
                        import cadquery as _cq
                        _shape = _cq.importers.importStep(step_path)
                        _bb = _shape.val().BoundingBox()
                        expected_bbox = {
                            "x": round(_bb.xlen, 1),
                            "y": round(_bb.ylen, 1),
                            "z": round(_bb.zlen, 1),
                        }
                    except Exception:
                        expected_bbox = None

                print(f"  [Onshape] Verifying upload...")
                verification = self.verify_upload(did, wid, expected_bbox)
                result["verification"] = verification

                # Use the Part Studio URL (not the blob URL)
                if verification.get("url"):
                    result["url"] = verification["url"]

                if verification["verified"]:
                    ob = verification.get("bbox", {})
                    bbox_str = ""
                    if ob:
                        bbox_str = f", bbox {ob.get('x_mm', '?')}x{ob.get('y_mm', '?')}x{ob.get('z_mm', '?')}mm"
                    print(f"  [Onshape] UPLOAD OK: {verification['parts']} part(s){bbox_str}")

                    # Deep geometry verification against spec
                    v_did = upload["documentId"]
                    v_wid = upload["workspaceId"]
                    v_eid = verification.get("part_studio_eid", "")
                    geo_check = self.verify_geometry(
                        step_path, spec, goal, v_did, v_wid, v_eid)
                    result["geometry_verification"] = geo_check

                    if geo_check["verified"]:
                        print(f"  [Onshape] GEOMETRY VERIFIED: all checks passed")
                        for c in geo_check["checks"]:
                            print(f"    {c['name']}: {c['actual']} {'OK' if c['passed'] else 'FAIL'}")
                    else:
                        print(f"  [Onshape] GEOMETRY ISSUES:")
                        for c in geo_check["checks"]:
                            status = "OK" if c["passed"] else "FAIL"
                            print(f"    [{status}] {c['name']}: expected {c['expected']}, got {c['actual']}")
                        result["errors"].extend(geo_check["issues"])

                    if geo_check.get("screenshot"):
                        print(f"  [Onshape] Screenshot: {geo_check['screenshot']}")
                        result["screenshot"] = geo_check["screenshot"]

                    return result
                elif verification["parts"] > 0:
                    # Parts exist but with warnings — still usable
                    for iss in verification["issues"]:
                        print(f"  [Onshape] WARNING: {iss}")
                    print(f"  [Onshape] {verification['parts']} part(s) created (with warnings)")
                    return result
                else:
                    # Translation produced 0 parts — fall back to features
                    for iss in verification["issues"]:
                        print(f"  [Onshape] WARNING: {iss}")
                    print(f"  [Onshape] Upload produced 0 parts — falling back to features")
                    result["errors"].extend(verification["issues"])
            except Exception as exc:
                print(f"  [Onshape] STEP upload failed ({exc}), falling back to features")
                result["errors"].append(f"STEP upload: {exc}")

        # FALLBACK: Build parametric features from spec
        try:
            print(f"  [Onshape] Creating document: {name}")
            doc = self.create_document(name)
            did, wid, eid = doc["documentId"], doc["workspaceId"], doc["elementId"]
            result["url"] = doc["url"]
            result["documentId"] = did

            features = self._spec_to_features(spec, goal)
            print(f"  [Onshape] Adding {len(features)} features...")

            for i, feat in enumerate(features):
                try:
                    self.add_feature(did, wid, eid, feat)
                    result["features_added"] += 1
                except Exception as exc:
                    result["errors"].append(f"Feature {i}: {exc}")
                    print(f"  [Onshape] Feature {i} failed: {exc}")

            result["method"] = "parametric_features"
            print(f"  [Onshape] Part created: {doc['url']}")
            print(f"  [Onshape] {result['features_added']}/{len(features)} features added")

            # Create an Onshape Drawing linked to this part
            try:
                drawing = self.create_drawing(did, wid, eid, f"{name} Drawing")
                if drawing.get("url"):
                    result["drawing_url"] = drawing["url"]
                    print(f"  [Onshape] Drawing: {drawing['url']}")
            except Exception:
                pass  # drawing creation is optional

        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
            print(f"  [Onshape] Error: {exc}")

        return result

    def _spec_to_features(self, spec: dict, goal: str = "") -> list[dict]:
        """Convert ARIA spec to Onshape feature list."""
        features = []
        goal_lower = goal.lower()

        # Determine base shape
        width = spec.get("width_mm", 100) / 1000  # convert to meters
        height = spec.get("height_mm", spec.get("depth_mm", 60)) / 1000
        thickness = spec.get("thickness_mm", spec.get("depth_mm", 10)) / 1000
        od = spec.get("od_mm", 0) / 1000
        bore = spec.get("bore_mm", 0) / 1000

        if od > 0:
            # Cylindrical part — sketch circle, extrude
            sketch_entities = [_make_sketch_circle(0, 0, od / 2, "outer")]
            features.append(_make_sketch_feature("Base Sketch", "top", sketch_entities))
            features.append(_make_extrude_feature("Base Extrude", "Base Sketch", thickness, "NEW"))

            # Bore
            if bore > 0:
                bore_entities = [_make_sketch_circle(0, 0, bore / 2, "bore")]
                features.append(_make_sketch_feature("Bore Sketch", "top", bore_entities))
                features.append(_make_extrude_feature("Bore Cut", "Bore Sketch", thickness + 0.001, "CUT"))
        else:
            # Box part — sketch rectangle, extrude
            sketch_entities = _make_sketch_rect(0, 0, width, height)
            features.append(_make_sketch_feature("Base Sketch", "top", sketch_entities))
            features.append(_make_extrude_feature("Base Extrude", "Base Sketch", thickness, "NEW"))

        # Bolt holes
        n_bolts = spec.get("n_bolts", 0)
        bolt_dia = spec.get("bolt_dia_mm", 6) / 1000
        if n_bolts > 0 and (width > 0 or od > 0):
            import math
            if od > 0:
                # Circular bolt pattern
                bcr = spec.get("bolt_circle_r_mm", od * 1000 * 0.35) / 1000
                bolt_entities = []
                for i in range(n_bolts):
                    angle = i * 2 * math.pi / n_bolts
                    cx = bcr * math.cos(angle)
                    cy = bcr * math.sin(angle)
                    bolt_entities.append(_make_sketch_circle(cx, cy, bolt_dia / 2, f"bolt_{i}"))
            else:
                # Rectangular bolt pattern (corners with margin)
                margin = min(width, height) * 0.15
                bolt_entities = []
                if n_bolts == 4:
                    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
                        cx = sx * (width / 2 - margin)
                        cy = sy * (height / 2 - margin)
                        bolt_entities.append(_make_sketch_circle(cx, cy, bolt_dia / 2, f"bolt_{i}"))
                else:
                    # Line pattern along width
                    for i in range(n_bolts):
                        cx = -width / 2 + margin + (width - 2 * margin) * i / max(n_bolts - 1, 1)
                        bolt_entities.append(_make_sketch_circle(cx, 0, bolt_dia / 2, f"bolt_{i}"))

            features.append(_make_sketch_feature("Bolt Holes Sketch", "top", bolt_entities))
            features.append(_make_extrude_feature("Bolt Holes", "Bolt Holes Sketch",
                                                   thickness + 0.001, "CUT"))

        return features


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_onshape_part(name: str, spec: dict[str, Any], goal: str = "",
                        step_path: str = "") -> dict[str, Any]:
    """Create a part in Onshape. Returns dict with url and status.
    If step_path is provided, uploads the STEP file directly (full fidelity)."""
    bridge = OnshapeBridge()
    return bridge.create_part(name, spec, goal, step_path=step_path)


def is_onshape_available() -> bool:
    """Check if Onshape API keys are configured."""
    return OnshapeBridge().is_available
