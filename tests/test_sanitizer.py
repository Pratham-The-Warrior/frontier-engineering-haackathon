"""
Unit tests for the Sanitizer Tool (Zero-Trust Secret & PII Scrubbing).
"""

import unittest
from tools.sanitizer import sanitize_text, sanitize_dict, sanitize_event_payload


class TestSanitizer(unittest.TestCase):

    def test_aws_key_redaction(self):
        text = "Deploy failed with AWS key AKIAIOSFODNN7EXAMPLE in region us-east-1"
        sanitized = sanitize_text(text)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", sanitized)
        self.assertIn("[REDACTED_AWS_KEY]", sanitized)

    def test_github_token_redaction(self):
        text = "Using git clone with token ghp_1234567890abcdefghijklmnopqrstuvwxyz12"
        sanitized = sanitize_text(text)
        self.assertNotIn("ghp_1234567890abcdefghijklmnopqrstuvwxyz12", sanitized)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", sanitized)

    def test_slack_token_redaction(self):
        text = "Bot token configured: xoxb-123456789012-1234567890123-abcdef123456"
        sanitized = sanitize_text(text)
        self.assertNotIn("xoxb-123456789012-1234567890123-abcdef123456", sanitized)
        self.assertIn("[REDACTED_SLACK_TOKEN]", sanitized)

    def test_jwt_redaction(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        text = f"Authorization failed for token {jwt}"
        sanitized = sanitize_text(text)
        self.assertNotIn(jwt, sanitized)
        self.assertIn("[REDACTED_JWT_TOKEN]", sanitized)

    def test_database_connection_string_redaction(self):
        uri = "postgres://db_user:SuperSecretPass123!@db-prod.internal.net:5432/orders_db"
        sanitized = sanitize_text(uri)
        self.assertNotIn("SuperSecretPass123!", sanitized)
        self.assertIn("db-prod.internal.net", sanitized)
        self.assertIn("[REDACTED_PASSWORD]", sanitized)

    def test_nested_dict_sanitization(self):
        payload = {
            "service": "auth-service",
            "password": "ClearTextPassword!",
            "api_key": "sk-1234567890abcdef1234567890",
            "details": {
                "user_token": "Bearer ghp_abcdef1234567890abcdef1234567890abcd",
                "nested_pass": "Secret999",
            }
        }
        sanitized = sanitize_dict(payload)
        self.assertEqual(sanitized["password"], "[REDACTED_CREDENTIAL]")
        self.assertEqual(sanitized["api_key"], "[REDACTED_CREDENTIAL]")
        self.assertNotIn("ClearTextPassword!", str(sanitized))
        self.assertNotIn("Secret999", str(sanitized))


if __name__ == "__main__":
    unittest.main()
