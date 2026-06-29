import unittest

from provenance_guard import (
    HIGH_CONFIDENCE_AI_LABEL,
    HIGH_CONFIDENCE_HUMAN_LABEL,
    UNCERTAIN_LABEL,
    ProvenanceService,
)


AI_LIKE_CONTENT = (
    "This system produces polished content with steady rhythm and repeated structure. "
    "This system produces polished content with steady rhythm and repeated structure. "
    "This system produces polished content with steady rhythm and repeated structure."
)
HUMAN_LIKE_CONTENT = (
    "At dawn I carried a ladder through wet basil, dropped one glove in the mud, laughed, then rewrote the opening line "
    "three times because it sounded too neat. By lunch the draft had a crooked joke, a memory about my uncle's transistor "
    "radio, and one abrupt sentence. Fine. I kept it."
)
UNCERTAIN_CONTENT = (
    "The lantern glowed over the desk while I revised the paragraph again and again. "
    "Each pass made the lines a little cleaner, though the rhythm still felt deliberate."
)


class ProvenanceServiceTests(unittest.TestCase):
    def test_submit_returns_high_confidence_ai_label(self) -> None:
        service = ProvenanceService()

        response = service.submit_content(AI_LIKE_CONTENT, creator_id="writer-1", client_id="client-1")

        self.assertEqual(response["attribution_result"], "high-confidence-ai")
        self.assertEqual(response["transparency_label"], HIGH_CONFIDENCE_AI_LABEL)
        self.assertGreaterEqual(response["confidence_score"], 0.5)
        self.assertEqual(len(response["signals_used"]), 2)

    def test_submit_returns_high_confidence_human_label(self) -> None:
        service = ProvenanceService()

        response = service.submit_content(HUMAN_LIKE_CONTENT, creator_id="writer-2", client_id="client-2")

        self.assertEqual(response["attribution_result"], "high-confidence-human")
        self.assertEqual(response["transparency_label"], HIGH_CONFIDENCE_HUMAN_LABEL)
        self.assertGreaterEqual(response["confidence_score"], 0.5)

    def test_submit_returns_uncertain_when_signals_are_mixed(self) -> None:
        service = ProvenanceService()

        response = service.submit_content(UNCERTAIN_CONTENT, creator_id="writer-3", client_id="client-3")

        self.assertEqual(response["attribution_result"], "uncertain")
        self.assertEqual(response["transparency_label"], UNCERTAIN_LABEL)
        self.assertLess(response["confidence_score"], 0.5)

    def test_appeal_marks_submission_under_review_and_logs_it(self) -> None:
        service = ProvenanceService()
        submission = service.submit_content(HUMAN_LIKE_CONTENT, creator_id="writer-4", client_id="client-4")

        appeal = service.file_appeal(submission["content_id"], "I can share earlier drafts and notes.")

        self.assertEqual(appeal["status"], "under review")
        audit_log = service.get_audit_log()["entries"]
        self.assertEqual(len(audit_log), 2)
        self.assertEqual(audit_log[-1]["event"], "appeal")
        self.assertEqual(audit_log[-1]["appeal_reason"], "I can share earlier drafts and notes.")

    def test_submission_rate_limit_blocks_excess_requests(self) -> None:
        service = ProvenanceService(submission_limit=2, submission_window_seconds=60)

        service.submit_content(HUMAN_LIKE_CONTENT, client_id="burst-client")
        service.submit_content(HUMAN_LIKE_CONTENT, client_id="burst-client")

        with self.assertRaisesRegex(Exception, "rate limit exceeded"):
            service.submit_content(HUMAN_LIKE_CONTENT, client_id="burst-client")


if __name__ == "__main__":
    unittest.main()
