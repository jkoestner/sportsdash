import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))  # make `sportsdash` importable without installing
sys.path.insert(0, str(HERE))  # make `conftest` importable for CFG

# Serve ESPN responses from fixtures and pin "today" before anything imports the app.
os.environ["SPORTSDASH_FIXTURES"] = str(HERE / "fixtures")
os.environ["SPORTSDASH_TODAY"] = "2026-10-02"

from sportsdash.config import load_config  # noqa: E402

CFG = load_config()
