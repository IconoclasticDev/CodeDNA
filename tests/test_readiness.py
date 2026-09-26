import unittest

from codedna.readiness import readiness_report


class ReadinessTests(unittest.TestCase):
    def test_demo_and_evidence_readiness_are_separate(self):
        report = readiness_report()
        self.assertTrue(report["demo_ready"])
        self.assertIn(report["status"], {"demo_ready_awaiting_real_evaluation", "competition_ready"})
        self.assertIn("held_out_evaluation", report["gates"])
        self.assertIn("trained_fusion", report["gates"])


if __name__ == "__main__":
    unittest.main()

