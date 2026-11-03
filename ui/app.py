"""ChainSight Streamlit entry point — delegates to multipage Home."""

import runpy
import sys
from pathlib import Path

_ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

home_script = str(Path(__file__).parent / "Home.py")
runpy.run_path(home_script, run_name="__main__")
