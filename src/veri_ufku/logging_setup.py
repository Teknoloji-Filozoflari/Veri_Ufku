"""Allowlisted technical events; exception text, paths and data are never logged."""

import json
import logging
import os
import stat
from logging.handlers import RotatingFileHandler


def private_stream(path, mode):
    fd = os.open(
        path,
        os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OSError("Log must be a private regular file")
        os.fchmod(fd, 0o600)
        stream = os.fdopen(fd, mode, encoding="utf-8")
    except BaseException:
        os.close(fd)
        raise
    return stream


class PrivateRotatingHandler(RotatingFileHandler):
    def _open(self):
        return private_stream(self.baseFilename, self.mode)


class EventLog:
    def __init__(self, state_dir):
        self.logger = logging.getLogger(f"veri_ufku.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        path = state_dir / "application.log"
        # Private even when a user's umask is permissive.
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
