"""install.sh links the skills of this repo into Claude Code and OpenCode.

Each test runs the script with HOME and XDG_CONFIG_HOME in a temporary directory, so no test
touches the real configuration.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "install.sh"
# The bash of macOS is 3.2; the script must run there too.
BASH = "/bin/bash" if Path("/bin/bash").exists() else "bash"
SKILLS = sorted(p.name for p in (REPO / "skills").iterdir() if (p / "SKILL.md").is_file())


class InstallCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.claude = self.home / ".claude" / "skills"
        self.opencode = self.home / "xdg" / "opencode" / "skills"

    def tearDown(self):
        self.tmp.cleanup()

    def run_install(self, *args, script=SCRIPT, xdg=True):
        env = {"PATH": "/usr/bin:/bin", "HOME": str(self.home)}
        if xdg:
            env["XDG_CONFIG_HOME"] = str(self.home / "xdg")
        return subprocess.run([BASH, str(script), *args], env=env, capture_output=True, text=True)

    def assert_linked(self, directory):
        for name in SKILLS:
            link = directory / name
            self.assertTrue(link.is_symlink(), link)
            self.assertEqual(link.resolve(), REPO / "skills" / name)

    def test_no_target_prints_usage_and_fails(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)

    def test_unknown_flag_fails(self):
        self.assertEqual(self.run_install("--codex").returncode, 2)

    def test_claude_links_every_skill(self):
        result = self.run_install("--claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_linked(self.claude)

    def test_opencode_links_every_skill_under_xdg_config(self):
        result = self.run_install("--opencode")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_linked(self.opencode)

    def test_opencode_skips_a_skill_that_claude_already_links(self):
        # OpenCode also reads ~/.claude/skills; a second link would show each skill twice.
        result = self.run_install("--claude", "--opencode")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_linked(self.claude)
        for name in SKILLS:
            self.assertFalse((self.opencode / name).exists(), name)
        self.assertIn("OpenCode reads", result.stdout)

    def test_second_run_changes_nothing(self):
        self.run_install("--opencode")
        result = self.run_install("--opencode")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_linked(self.opencode)
        self.assertIn("already linked", result.stdout)

    def test_never_replaces_a_foreign_entry(self):
        self.opencode.mkdir(parents=True)
        foreign = self.opencode / SKILLS[0]
        foreign.mkdir()
        result = self.run_install("--opencode")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(foreign.is_dir() and not foreign.is_symlink())
        self.assertIn(str(foreign), result.stderr)
        for name in SKILLS[1:]:
            self.assertTrue((self.opencode / name).is_symlink(), name)

    def test_opencode_falls_back_to_dot_config(self):
        result = self.run_install("--opencode", xdg=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_linked(self.home / ".config" / "opencode" / "skills")

    def test_warns_about_an_opencode_link_that_now_duplicates_claude(self):
        self.run_install("--opencode")
        result = self.run_install("--claude", "--opencode")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_linked(self.opencode)  # never removed
        for name in SKILLS:
            self.assertIn(f"remove {self.opencode / name}", result.stderr)

    def test_reports_a_dangling_link_and_keeps_it(self):
        self.claude.mkdir(parents=True)
        dangling = self.claude / SKILLS[0]
        dangling.symlink_to(self.home / "gone")
        result = self.run_install("--claude")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(dangling.is_symlink())
        self.assertIn(f"dangling link, not replaced: {dangling}", result.stderr)

    def test_fails_when_it_finds_no_skills(self):
        # A symlink to the script resolves the repo to the directory of the link.
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        (bin_dir / "install.sh").symlink_to(SCRIPT)
        result = self.run_install("--claude", script=bin_dir / "install.sh")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no skills found under", result.stderr)


if __name__ == "__main__":
    unittest.main()
