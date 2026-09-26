"""Small dependency-free HTTP server for the CodeDNA prototype."""

from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .demo import demo_bundle
from .fusion import load_default_model
from .ingest import collect_payload_files
from .profile import build_profile
from .representation import provider_status
from .readiness import readiness_report
from .scoring import analyze_submission
from .storage import load_profile, save_profile

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
MAX_REQUEST_BYTES = 36_000_000
RESULTS_PATH = ROOT / "work" / "evaluation" / "results.json"


def public_profile(profile: dict) -> dict:
    private = {"stats", "source_files", "semantic_centroid"}
    public = {key: value for key, value in profile.items() if key not in private}
    # Vercel and other serverless hosts may route the next request to a fresh
    # instance. Return only derived profile statistics required for analysis;
    # historical source code is never included in this client-side context.
    public["analysis_context"] = {
        key: profile[key]
        for key in ("id", "name", "stats", "semantic_centroid", "representation_name")
        if key in profile
    }
    return public


class Handler(BaseHTTPRequestHandler):
    server_version = "CodeDNA/0.1"

    def log_message(self, format: str, *args) -> None:
        print(f"[codedna] {self.address_string()} - {format % args}")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
        )

    def _error(self, status: int, code: str, message: str, recovery: str) -> None:
        self._json({"error": {"code": code, "message": message, "recovery": recovery}}, status)

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid content length.") from exc
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("Request body must be between 1 byte and 36 MB.")
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            representation = provider_status()
            loaded_model = load_default_model()
            compatible_model = bool(loaded_model and loaded_model.representation == representation["configured"])
            self._json(
                {
                    "status": "ready" if representation["available"] else "degraded",
                    "service": "ready",
                    "features": {"lexical": True, "structural": True, "complexity": True, "representation": representation},
                    "fusion_model": "trained" if compatible_model else "baseline-v2",
                    "version": "0.2.0",
                }
            )
            return
        if path == "/api/model":
            model = load_default_model()
            representation = provider_status()
            compatible = bool(model and model.representation == representation["configured"])
            evaluation = None
            if RESULTS_PATH.is_file():
                try:
                    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
                    evaluation = {
                        "dataset": results.get("dataset"),
                        "summary": results.get("evaluation", {}).get("summary"),
                        "calibrated_thresholds": results.get("evaluation", {}).get("calibrated_thresholds"),
                        "limitation": results.get("limitation"),
                    }
                except (OSError, json.JSONDecodeError):
                    evaluation = None
            self._json(
                {
                    "active_model": model.name if compatible else "deterministic-baseline-v2",
                    "trained": compatible,
                    "trained_artifact_present": bool(model),
                    "trained_artifact_compatible": compatible,
                    "representation": representation,
                    "evaluation_available": evaluation is not None,
                    "evaluation": evaluation,
                }
            )
            return
        if path == "/api/readiness":
            self._json(readiness_report())
            return
        if path.startswith("/api/demo/"):
            case = path.rsplit("/", 1)[-1]
            if case not in {"consistent", "review", "mixed"}:
                self._error(404, "demo_not_found", "That demo case does not exist.", "Choose consistent, review or mixed.")
                return
            self._json(demo_bundle(case))
            return
        if path.startswith("/api/profiles/"):
            profile_id = path.rsplit("/", 1)[-1]
            profile = load_profile(profile_id)
            if not profile:
                self._error(404, "profile_not_found", "The requested profile was not found.", "Build a new profile.")
                return
            self._json(public_profile(profile))
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._body()
            if path == "/api/profiles":
                files, sources = collect_payload_files(payload)
                profile = build_profile(str(payload.get("name", "Developer")), files)
                profile["sources"] = sources
                save_profile(profile)
                self._json(public_profile(profile), 201)
                return
            if path.startswith("/api/profiles/") and path.endswith("/analyze"):
                profile_id = path.split("/")[3]
                profile = load_profile(profile_id)
                if not profile:
                    context = payload.get("profile_context")
                    if isinstance(context, dict) and context.get("id") == profile_id:
                        profile = context
                if not profile:
                    self._error(404, "profile_not_found", "The requested profile was not found.", "Build a new profile.")
                    return
                files, _ = collect_payload_files(payload)
                self._json(analyze_submission(profile, files))
                return
            self._error(404, "route_not_found", "That API route does not exist.", "Check the API path.")
        except ValueError as exc:
            self._error(422, "invalid_input", str(exc), "Correct the input and try again.")
        except Exception:
            self._error(500, "analysis_failed", "The analysis could not be completed.", "Try a smaller input or use the demo case.")

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (FRONTEND / relative).resolve()
        try:
            candidate.relative_to(FRONTEND.resolve())
        except ValueError:
            self._error(403, "forbidden", "That path cannot be served.", "Return to the application home page.")
            return
        if not candidate.is_file():
            candidate = FRONTEND / "index.html"
        body = candidate.read_bytes()
        mime, _ = mimetypes.guess_type(candidate.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"CodeDNA is running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run(port=int(os.environ.get("CODEDNA_PORT", "8000")))
