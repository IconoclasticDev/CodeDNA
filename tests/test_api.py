import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from codedna.demo import CONSISTENT, HISTORY
from codedna.server import Handler


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if data is not None else "GET",
        )
        return json.load(urllib.request.urlopen(request, timeout=3))

    def test_health_and_demo_routes(self):
        raw_health = urllib.request.urlopen(self.base + "/api/health", timeout=3)
        health = json.load(raw_health)
        model = self.request("/api/model")
        readiness = self.request("/api/readiness")
        demo = self.request("/api/demo/review")
        mixed = self.request("/api/demo/mixed")
        self.assertEqual(health["status"], "ready")
        self.assertEqual(raw_health.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", raw_health.headers["Content-Security-Policy"])
        self.assertIn("active_model", model)
        self.assertTrue(readiness["demo_ready"])
        self.assertIn("real_dataset", readiness["gates"])
        self.assertEqual(demo["report"]["verdict"], "Review Recommended")
        self.assertGreater(demo["report"]["function_breakdown_total"], 0)
        self.assertEqual(mixed["report"]["file_breakdown_total"], 2)
        self.assertEqual(mixed["report"]["file_breakdown"][0]["name"], "shifted_solution.py")

    def test_static_pages_are_separated(self):
        landing = urllib.request.urlopen(self.base + "/", timeout=3).read().decode("utf-8")
        analyze = urllib.request.urlopen(self.base + "/analyze.html", timeout=3).read().decode("utf-8")
        evidence = urllib.request.urlopen(self.base + "/evidence.html", timeout=3).read().decode("utf-8")
        self.assertIn("Start an analysis", landing)
        self.assertNotIn("CodeDNA workspace", landing)
        self.assertIn("CodeDNA workspace", analyze)
        self.assertNotIn("COMPETITION READINESS", analyze)
        self.assertIn("COMPETITION READINESS", evidence)
        self.assertNotIn("CodeDNA workspace", evidence)
    def test_profile_to_analysis_golden_path(self):
        profile = self.request("/api/profiles", {"name": "API test", "files": HISTORY})
        report = self.request(f"/api/profiles/{profile['id']}/analyze", {"files": CONSISTENT})
        self.assertEqual(report["profile_id"], profile["id"])
        self.assertIn(report["verdict"], {"Consistent", "Uncertain"})
        self.assertIn("analysis_context", profile)
        self.assertNotIn("source_files", profile["analysis_context"])

    def test_stateless_profile_context_supports_serverless_analysis(self):
        profile = self.request("/api/profiles", {"name": "Serverless test", "files": HISTORY})
        missing_id = profile["id"] + "x"
        context = dict(profile["analysis_context"])
        context["id"] = missing_id
        report = self.request(
            f"/api/profiles/{missing_id}/analyze",
            {"files": CONSISTENT, "profile_context": context},
        )
        self.assertEqual(report["profile_id"], missing_id)

    def test_invalid_profile_returns_structured_error(self):
        request = urllib.request.Request(
            self.base + "/api/profiles",
            data=json.dumps({"name": "Empty"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=3)
        payload = json.load(context.exception)
        self.assertEqual(context.exception.code, 422)
        self.assertEqual(payload["error"]["code"], "invalid_input")


if __name__ == "__main__":
    unittest.main()


