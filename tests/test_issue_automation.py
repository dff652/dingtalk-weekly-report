import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "issue-assistance.yml"


class IssueAutomationTests(unittest.TestCase):
    def test_workflow_only_posts_a_fixed_opened_issue_reply(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("types: [opened]", text)
        self.assertNotIn("labeled", text)
        self.assertNotIn("issue_comment:", text)
        self.assertNotIn("ai-triage", text)

    def test_workflow_has_no_model_or_repository_write_access(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("permissions: {}", text)
        self.assertIn("issues: write", text)
        self.assertNotIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("pull-requests:", text)
        self.assertNotIn("ANTHROPIC_API_KEY", text)
        self.assertNotIn("OPENAI_API_KEY", text)

    def test_reply_does_not_mention_github_users(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("@", text)
        self.assertIn("外部提及不会自动调用 AI", text)


if __name__ == "__main__":
    unittest.main()
