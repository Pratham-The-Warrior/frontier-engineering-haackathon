"""
Unit tests for the Jira Collector and ADF text extraction.
"""

import unittest
from collectors.jira_collector import parse_pasted_jira_tickets, _extract_adf_text


class TestJiraCollector(unittest.TestCase):

    def test_parse_pasted_jira_tickets(self):
        text = """
        PROD-1024 [P1] [Resolved] Database connection pool exhausted in auth service
        INFRA-501 [P2] [Open] Upgrade Redis cache cluster to v7.2
        """
        tickets = parse_pasted_jira_tickets(text)
        self.assertEqual(len(tickets), 2)
        self.assertEqual(tickets[0]["key"], "PROD-1024")
        self.assertEqual(tickets[0]["priority"], "P1")
        self.assertEqual(tickets[0]["status"], "Resolved")
        self.assertIn("Database connection pool", tickets[0]["summary"])

    def test_extract_adf_text(self):
        adf_doc = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Post-mortem investigation for incident "},
                        {"type": "text", "text": "PROD-9988"},
                    ],
                }
            ],
        }
        text = _extract_adf_text(adf_doc)
        self.assertIn("Post-mortem investigation for incident PROD-9988", text)


if __name__ == "__main__":
    unittest.main()
