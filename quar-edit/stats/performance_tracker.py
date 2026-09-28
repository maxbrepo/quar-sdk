from __future__ import annotations
import json, statistics
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class PerformanceSample:
    language: str
    toolchain: str
    mode: str
    duration_seconds: float
    exit_code: int

def summarize(samples: list[PerformanceSample]) -> dict:
    """Return minimum, median and mean execution duration."""
    values=[s.duration_seconds for s in samples]
    if not values: return {"runs":0,"min":None,"median":None,"mean":None}
    return {"runs":len(values),"min":min(values),"median":statistics.median(values),
            "mean":statistics.fmean(values)}

def save_samples(path: Path, samples: list[PerformanceSample]) -> None:
    """Persist benchmark samples as readable JSON."""
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps([asdict(s) for s in samples],indent=2),encoding="utf-8")
