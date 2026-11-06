import json
import logging
import re

_TOKEN = re.compile(r"token=[^&\s\"]+")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })


class RedactTokens(logging.Filter):
    """Keep per-call tokens out of access logs (they ride in the WS query string)."""

    def filter(self, record):
        if record.args:
            record.args = tuple(_TOKEN.sub("token=***", a) if isinstance(a, str) else a for a in record.args)
        record.msg = _TOKEN.sub("token=***", str(record.msg))
        return True


def configure_logging(fmt: str = "text") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if fmt == "json" else
                         logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    handler.addFilter(RedactTokens())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers, lg.propagate = [], True
