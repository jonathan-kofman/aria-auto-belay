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
                return result
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
