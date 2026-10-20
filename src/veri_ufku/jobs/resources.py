"""Lightweight shared Linux RSS probe; importing it never initializes a backend."""

import os
from pathlib import Path


def rss_bytes(pid):
    try:
        with open(f"/proc/{pid}/statm") as stream:
            return int(stream.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return 0


def process_tree(pid):
    """Owned descendants, including children created by native libraries."""
    found, pending = set(), [pid]
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        try:
            for task in Path(f"/proc/{current}/task").iterdir():
                pending.extend(int(p) for p in (task / "children").read_text().split())
        except (OSError, ValueError):
            pass
    return found


def process_identity(pid):
    try:
        # comm may contain spaces/parentheses; fields following the final ')' are fixed.
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def terminate_identity(pid, identity):
    """Linux pidfd prevents killing a different process after PID reuse."""
    import signal

    if identity is None:
        return
    try:
        fd = os.pidfd_open(pid)
    except ProcessLookupError:
        return
    try:
        if process_identity(pid) == identity:
            signal.pidfd_send_signal(fd, signal.SIGKILL)
    finally:
        os.close(fd)
