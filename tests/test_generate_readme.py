import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_readme import (  # noqa: E402
    load_config,
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

        self.assertIn("| Project | Description | Language |", rendered)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", rendered)
        self.assertIn("img.shields.io", rendered)
        self.assertIn("Python", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertNotIn("Topics:", rendered)

    def test_render_projects_url_encodes_hash_in_language_names(self):
        repository = {
            "name": "csharp-project",
            "url": "https://github.com/example/csharp-project",
            "description": "A C# project",
            "primaryLanguage": {"name": "C#"},
        }

        rendered = render_projects(
            [repository],
            {"show_language": True},
        )

        self.assertIn("%23", rendered)
        self.assertNotIn("-C#-", rendered)
        self.assertIn("-C%23-", rendered)

    def test_render_projects_includes_valid_homepage_link_in_description(self):
        repository = {
            "name": "mind-5",
            "url": "https://github.com/example/mind-5",
            "homepageUrl": "https://example.com/app?mode=daily&view=(today)",
            "description": "Daily puzzles",
        }

        rendered = render_projects([repository], {"show_language": False})

        self.assertIn(
            "[Website](<https://example.com/app?mode=daily&view=%28today%29>)",
            rendered,
        )

    def test_load_config_accepts_optional_website_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "projects.yml"
            path.write_text(
                "owner: example\n"
                "projects:\n"
                "  - repo: mind-5\n"
                "    website: https://example.com/app\n",
                encoding="utf-8",
            )

            owner, projects, _ = load_config(path)

        self.assertEqual(owner, "example")
        self.assertEqual(
            projects,
            [{"repo": "mind-5", "website": "https://example.com/app"}],
        )

    def test_load_config_rejects_unsafe_website_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "projects.yml"
            path.write_text(
                "owner: example\n"
                "projects:\n"
                "  - repo: mind-5\n"
                "    website: javascript:alert(1)\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "valid HTTP\\(S\\) URL"):
                load_config(path)

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
