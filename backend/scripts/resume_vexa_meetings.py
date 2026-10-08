"""Recover scoped Vexa bridge tasks after an interrupted worker."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.workers.vexa_meeting import resume_existing_bridges
print(f"Resumed {resume_existing_bridges()} Vexa meeting bridges")
