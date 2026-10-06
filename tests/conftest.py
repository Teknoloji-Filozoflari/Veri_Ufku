import os

# Set before importing Qt; each test config/cache/state is an isolated fixture.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
