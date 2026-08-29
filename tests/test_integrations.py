import unittest
from integrations.enterprise_integrations import format_slack_blocks, export_jira_tickets, handle_pagerduty_webhook


class TestEnterpriseIntegrations(unittest.TestCase):
    def test_format_slack_blocks(self):
        report = """
# Post-Mortem Report: DB Exhaustion
## Executive Summary
The database connection pool was exhausted because timeout limit configuration was omitted in the migration. The hotfix was deployed to restore the system.
## Impact
Affected user-service.
"""
        res = format_slack_blocks(report, incident_title="DB Exhaustion", severity="P1")
        self.assertIn("blocks", res)
        blocks = res["blocks"]
        self.assertGreaterEqual(len(blocks), 3)
        self.assertEqual(blocks[0]["type"], "header")
        self.assertIn("DB Exhaustion", blocks[0]["text"]["text"])
        self.assertIn("P1", blocks[1]["fields"][0]["text"])
        self.assertIn("The database connection pool was exhausted", blocks[2]["text"]["text"])

    def test_export_jira_tickets(self):
        # Action Items section format:
        # ## Action Items
        # | Priority | Type | Description | Owner |
        # |----------|------|-------------|-------|
        # | P0 | Prevent | Add CI validation for required keys | @backend |
        # | P1 | Detect | Add alerts at 70% threshold | @sre |
        
        report = """
## Action Items
| Priority | Type | Description | Owner |
|----------|------|-------------|-------|
| P0 | Prevent | Add CI validation for required database config keys | @backend |
| P1 | Detect | Add connection pool alerts at 70% threshold | @sre |
"""
        tickets = export_jira_tickets(report)
        self.assertEqual(len(tickets), 2)
        
        self.assertEqual(tickets[0]["project"]["key"], "INC")
        self.assertEqual(tickets[0]["issuetype"]["name"], "Task")
        self.assertIn("[P0]", tickets[0]["summary"])
        self.assertIn("[Prevent]", tickets[0]["summary"])
        self.assertIn("Add CI validation", tickets[0]["summary"])
        self.assertEqual(tickets[0]["priority"]["name"], "High")

        self.assertIn("[P1]", tickets[1]["summary"])
        self.assertIn("[Detect]", tickets[1]["summary"])
        self.assertEqual(tickets[1]["priority"]["name"], "High")

    def test_handle_pagerduty_webhook(self):
        payload = {
            "event": {
                "data": {
                    "id": "INC-12345",
                    "title": "Database Connection Error"
                }
            }
        }
        res = handle_pagerduty_webhook(payload)
        self.assertEqual(res["status"], "triggered")
        self.assertEqual(res["incident_id"], "INC-12345")
        self.assertEqual(res["title"], "Database Connection Error")
        self.assertIn("INC-12345", res["message"])


if __name__ == "__main__":
    unittest.main()
