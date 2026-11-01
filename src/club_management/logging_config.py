import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(*, log_file: Path | None = None, level: int = logging.INFO) -> None:
    """Configure UTC console logs and an optional rotating file."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
            )
        )
    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    formatter.converter = time.gmtime
    root = logging.getLogger()
    for handler in root.handlers[:]:
        if handler.name == "club_management":
            root.removeHandler(handler)
            handler.close()
    root.setLevel(level)
    for handler in handlers:
        handler.name = "club_management"
        handler.setLevel(level)
        handler.setFormatter(formatter)
        root.addHandler(handler)
    for name in ("O365", "msal"):
        logging.getLogger(name).setLevel(logging.WARNING)
