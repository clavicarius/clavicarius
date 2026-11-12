import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_readme import (  # noqa: E402
    render_projects,
    require_public_repository,
    update_readme,
)


class GenerateReadmeTests(unittest.TestCase):
    def test_update_readme_preserves_outside_content_and_is_idempotent(self):
        original = (
            "before\r\n"
            "<!-- PROJECTS:START -->\r\n"
            "old content\r\n"
            "<!-- PROJECTS:END -->\r\n"
            "after\r\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_bytes(original.encode("utf-8"))

            self.assertTrue(update_readme(path, "<p>new content</p>"))
            updated = path.read_bytes().decode("utf-8")
            self.assertEqual(
                updated,
                "before\r\n"
                "<!-- PROJECTS:START -->\r\n"
                "<p>new content</p>\r\n"
                "<!-- PROJECTS:END -->\r\n"
                "after\r\n",
            )
            self.assertFalse(update_readme(path, "<p>new content</p>"))

    def test_render_projects_escapes_metadata_and_uses_configured_columns(self):
        repository = {
            "name": 'A "project" <script>',
            "url": "https://github.com/example/project",
            "homepageUrl": "javascript:alert(1)",
            "description": "<img src=x onerror=alert(1)>",
            "openGraphImageUrl": "https://example.com/preview.png",
            "primaryLanguage": {"name": "Python", "color": "#3572A5"},
            "repositoryTopics": {"nodes": [{"topic": {"name": "safe&sound"}}]},
            "stargazers": {"totalCount": 4},
            "forks": {"totalCount": 2},
            "usesCustomOpenGraphImage": True,
        }

        rendered = render_projects(
            [repository],
            {
                "columns": 4,
                "show_language": True,
                "show_topics": True,
                "show_stars": True,
                "show_forks": True,
            },
        )

        self.assertIn('class="projects-table"', rendered)
        self.assertIn('class="project-cell"', rendered)
        self.assertIn('class="project-content"', rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", rendered)
        self.assertIn("safe&amp;sound", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertIn("<strong>Stars:</strong>", rendered)
        self.assertIn("<strong>Forks:</strong>", rendered)
        self.assertIn('<style>', rendered)
        self.assertIn('.project-cell', rendered)

    def test_non_public_repository_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "only PUBLIC repositories"):
            require_public_repository(
                {"visibility": "PRIVATE"},
                "example",
                "secret-project",
            )

    def test_missing_repository_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not found or is inaccessible"):
            require_public_repository(None, "example", "missing")


if __name__ == "__main__":
    unittest.main()
