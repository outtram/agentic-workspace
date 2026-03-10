"""CC debug logger — rotating file log for commands, chat, errors, and progress."""
import logging
from logging.handlers import RotatingFileHandler

from . import PROJECT_ROOT

_LOG_PATH = PROJECT_ROOT / ".claude" / "dashboards" / "cc-debug.log"
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("cc")
logger.setLevel(logging.DEBUG)

# 1 MB max, keep 2 backups
_handler = RotatingFileHandler(_LOG_PATH, maxBytes=1_000_000, backupCount=2)
_handler.setFormatter(
    logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)-20s  %(message)s", datefmt="%H:%M:%S")
)
logger.addHandler(_handler)

# Route brain.mail loggers to the same file so IMAP debug shows up
for _name in ("brain.mail.inbox", "brain.mail.outbox"):
    _sub = logging.getLogger(_name)
    _sub.setLevel(logging.DEBUG)
    _sub.addHandler(_handler)
