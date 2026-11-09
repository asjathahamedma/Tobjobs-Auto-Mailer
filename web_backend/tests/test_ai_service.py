import os
import unittest
from unittest.mock import patch

from pydantic import BaseModel

from web_backend.app.ai import AIBusyError, clear_ai_cache, redact_contact_details, run_structured_task


class ExampleSchema(BaseModel):
    role: str
    summary: str


class AIServicesTests(unittest.TestCase):
    def setUp(self):
        clear_ai_cache()
        os.environ["GROQ_API_KEY"] = "groq-key"
        os.environ["GEMINI_API_KEY"] = "gemini-key"
        os.environ["AI_PROVIDER_ORDER"] = "groq,gemini"

    def tearDown(self):
        clear_ai_cache()

    def test_redaction_removes_contact_details(self):
        prompt = "Reach jane.doe@example.com or +1 555 123 4567 at 123 Main Street, and the role is data engineer."
        redacted = redact_contact_details(prompt)
        self.assertNotIn("jane.doe@example.com", redacted)
        self.assertNotIn("555 123 4567", redacted)
        self.assertNotIn("123 Main Street", redacted)
        self.assertIn("data engineer", redacted)

    def test_fallback_uses_next_provider_on_error(self):
        with patch("web_backend.app.ai._request_provider_completion", side_effect=[
            AIBusyError("AI busy, will retry"),
            {"provider": "gemini", "model": "gemini-2.5-flash", "content": '{"role": "engineer", "summary": "works well"}', "input_tokens": 10, "output_tokens": 5, "latency_ms": 100},
        ]) as provider_call:
            result = run_structured_task(
                "fallback-test",
                "Return the matching role and summary.",
                {"title": "Software engineer"},
                ExampleSchema,
                provider_order=["groq", "gemini"],
            )
            self.assertEqual(result.role, "engineer")
            self.assertEqual(provider_call.call_count, 2)

    def test_invalid_json_triggers_repair_prompt(self):
        with patch("web_backend.app.ai._request_provider_completion", side_effect=[
            {"provider": "groq", "model": "llama-3.3-70b-versatile", "content": "not-json", "input_tokens": 20, "output_tokens": 5, "latency_ms": 100},
            {"provider": "groq", "model": "llama-3.3-70b-versatile", "content": '{"role": "analyst", "summary": "fixed"}', "input_tokens": 20, "output_tokens": 5, "latency_ms": 100},
        ]):
            result = run_structured_task(
                "repair-test",
                "Return the matching role and summary.",
                {"title": "Data analyst"},
                ExampleSchema,
                provider_order=["groq"],
            )
            self.assertEqual(result.role, "analyst")

    def test_cache_hits_do_not_repeat_provider_calls(self):
        with patch("web_backend.app.ai._request_provider_completion", return_value={
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "content": '{"role": "developer", "summary": "cached"}',
            "input_tokens": 12,
            "output_tokens": 5,
            "latency_ms": 50,
        }) as provider_call:
            first = run_structured_task("cache-test", "Return the matching role and summary.", {"title": "Backend developer"}, ExampleSchema, provider_order=["groq"])
            second = run_structured_task("cache-test", "Return the matching role and summary.", {"title": "Backend developer"}, ExampleSchema, provider_order=["groq"])
            self.assertEqual(first.role, "developer")
            self.assertEqual(second.role, "developer")
            self.assertEqual(provider_call.call_count, 1)

    def test_budget_throttling_rejects_over_limit(self):
        from web_backend.app.ai import _reserve_tokens

        with patch("web_backend.app.ai._provider_tpm_limit", return_value=1), patch("web_backend.app.ai._provider_daily_budget", return_value=1):
            _reserve_tokens("groq", 1, 0)
            with self.assertRaises(AIBusyError):
                _reserve_tokens("groq", 1, 0)


if __name__ == "__main__":
    unittest.main()
