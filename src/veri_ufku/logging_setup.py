"""Allowlisted technical events; exception text, paths and data are never logged."""

import json
import logging
import os
from logging.handlers import RotatingFileHandler


class PrivateRotatingHandler(RotatingFileHandler):
    def _open(self):
        fd = os.open(self.baseFilename, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        os.fchmod(fd, 0o600)
        return os.fdopen(fd, self.mode, encoding=self.encoding)


class EventLog:
    def __init__(self, state_dir):
        self.logger = logging.getLogger(f"veri_ufku.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        path = state_dir / "application.log"
        # Private even when a user's umask is permissive.
        fd = os.open(
            path,
            os.O_CREAT | os.O_APPEND | os.O_WRONLY,
            0o600,
        )
        os.close(fd)
        handler = PrivateRotatingHandler(path, maxBytes=256_000, backupCount=2)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self.logger.addHandler(handler)

    def event(self, event, job_id="", error=None):
        payload = {"event": event, "job_id": job_id}
        if error:
            payload.update(
                code=error.code,
                correlation_id=error.correlation_id,
                exception_type=error.exception_type,
            )
        self.logger.info(json.dumps(payload))

    def close(self):
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
