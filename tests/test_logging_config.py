import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from club_management.logging_config import setup_logging


class TestLoggingConfig(TestCase):
    def setUp(self) -> None:
        self.tmp_path = Path(self.enterContext(TemporaryDirectory()))

    def test_repeated_logging_setup_writes_one_record(self) -> None:
        root = logging.getLogger()
        level = root.level
        dependency_levels = {
            name: logging.getLogger(name).level for name in ("O365", "msal")
        }
        path = self.tmp_path / "application.log"
        try:
            setup_logging(log_file=path)
            setup_logging(log_file=path)
            logging.getLogger("example").info("Übertragung completed")
            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count("Übertragung completed"), 1)
            self.assertIn("Z INFO example:", content)
        finally:
            for handler in root.handlers[:]:
                if handler.name == "club_management":
                    root.removeHandler(handler)
                    handler.close()
            root.setLevel(level)
            for name, logger_level in dependency_levels.items():
                logging.getLogger(name).setLevel(logger_level)
