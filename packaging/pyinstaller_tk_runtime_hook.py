import os
import shutil
import sys
from pathlib import Path

def _bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

def _copy_tcl_runtime(source: Path, target: Path) -> None:
    init_file = target / "tcl8.6" / "init.tcl"
    tk_file = target / "tk8.6" / "tk.tcl"
    if init_file.exists() and tk_file.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(source, target)

source_dir = _bundle_root() / "tcl_runtime"
target_dir = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "FormuLabTcl"

if source_dir.exists():
    _copy_tcl_runtime(source_dir, target_dir)
    os.environ["TCL_LIBRARY"] = str(target_dir / "tcl8.6")
    os.environ["TK_LIBRARY"] = str(target_dir / "tk8.6")