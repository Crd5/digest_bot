import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ServiceSetupTests(unittest.TestCase):
    def write_setup_script(self, project_dir):
        script_path = project_dir / "setup_service.sh"
        script_path.write_text((PROJECT_ROOT / "setup_service.sh").read_text())
        script_path.chmod(0o755)
        return script_path

    def test_generated_systemd_unit_escapes_paths_and_uses_single_service(self):
        temp_dir = tempfile.TemporaryDirectory(prefix="digest bot %")
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name)
        script_path = self.write_setup_script(project_dir)
        python_path = project_dir / "venv" / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.touch()
        env_path = project_dir / ".env"
        session_path = project_dir / "digest_session.session"
        db_paths = [
            project_dir / "digest_bot.db",
            project_dir / "digest_bot.db-wal",
            project_dir / "digest_bot.db-shm",
        ]
        env_path.touch()
        session_path.touch()
        for db_path in db_paths:
            db_path.touch()
        env_path.chmod(0o644)
        session_path.chmod(0o644)
        for db_path in db_paths:
            db_path.chmod(0o644)

        result = subprocess.run(
            [str(script_path)],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        service_content = (project_dir / "tg-digest-bot.service").read_text()

        self.assertIn('WorkingDirectory="', service_content)
        self.assertIn('ExecStart="', service_content)
        self.assertIn("UMask=0077", service_content)
        self.assertIn("%%", service_content)
        self.assertIn("Telegram Read-Only AI Assistant", service_content)
        self.assertNotIn("digest_session.session file not found", result.stdout)
        self.assertEqual(0o600, env_path.stat().st_mode & 0o777)
        self.assertEqual(0o600, session_path.stat().st_mode & 0o777)
        self.assertTrue(all((db_path.stat().st_mode & 0o777) == 0o600 for db_path in db_paths))

    def test_setup_service_uses_script_directory_when_called_from_elsewhere(self):
        project_temp_dir = tempfile.TemporaryDirectory(prefix="digest bot %")
        other_temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(project_temp_dir.cleanup)
        self.addCleanup(other_temp_dir.cleanup)
        project_dir = Path(project_temp_dir.name)
        other_dir = Path(other_temp_dir.name)
        script_path = self.write_setup_script(project_dir)
        python_path = project_dir / "venv" / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.touch()

        subprocess.run(
            [str(script_path)],
            cwd=other_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        service_path = project_dir / "tg-digest-bot.service"
        self.assertTrue(service_path.exists())
        self.assertFalse((other_dir / "tg-digest-bot.service").exists())
        expected_project_dir = str(project_dir.resolve()).replace("%", "%%")
        self.assertIn(expected_project_dir, service_path.read_text())

    def test_setup_service_restricts_private_files_before_missing_venv_error(self):
        temp_dir = tempfile.TemporaryDirectory(prefix="digest bot %")
        self.addCleanup(temp_dir.cleanup)
        project_dir = Path(temp_dir.name)
        script_path = self.write_setup_script(project_dir)
        private_paths = [
            project_dir / ".env",
            project_dir / ".env.local",
            project_dir / "digest_session.session",
            project_dir / "digest_session.session-wal",
            project_dir / "digest_bot.db",
            project_dir / "digest_bot.db-wal",
        ]
        for path in private_paths:
            path.touch()
            path.chmod(0o644)

        result = subprocess.run(
            [str(script_path)],
            cwd=project_dir,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Virtual environment not found", result.stdout)
        self.assertTrue(all((path.stat().st_mode & 0o777) == 0o600 for path in private_paths))


class RepoHygieneTests(unittest.TestCase):
    def test_gitignore_excludes_sensitive_sidecars(self):
        candidates = [
            "digest_bot.db",
            "digest_bot.db-journal",
            "digest_bot.db-wal",
            "digest_bot.db-shm",
            "digest_session.session",
            "digest_session.session-journal",
            "digest_session.session-wal",
            "digest_session.session-shm",
            ".env",
            ".env.local",
        ]

        result = subprocess.run(
            ["git", "check-ignore", "-v", *candidates],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        ignored = {line.rsplit(maxsplit=1)[-1] for line in result.stdout.splitlines()}
        self.assertEqual(set(candidates), ignored)

    def test_project_instruction_file_is_trackable(self):
        result = subprocess.run(
            ["git", "check-ignore", "-v", "GEMINI.md"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)

    def test_docs_include_venv_safe_test_command_and_bot_env(self):
        expected_command = "venv/bin/python -m unittest discover -s tests"

        self.assertIn(expected_command, (PROJECT_ROOT / "README.md").read_text())
        self.assertIn(expected_command, (PROJECT_ROOT / "GEMINI.md").read_text())
        env_example = (PROJECT_ROOT / ".env.example").read_text()
        self.assertIn("BOT_TOKEN=", env_example)
        self.assertIn("OWNER_TELEGRAM_USER_ID=", env_example)


if __name__ == "__main__":
    unittest.main()
