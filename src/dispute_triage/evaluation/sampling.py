"""Draw a stratified sample for hand labeling (so rare classes are represented)."""
from __future__ import annotations

import csv
import random
from collections import defaultdict

from ..models import Complaint


def stratified_sample(complaints: list[Complaint], n: int = 300, seed: int = 42) -> list[Complaint]:
    rng = random.Random(seed)
    by_issue: dict[str, list[Complaint]] = defaultdict(list)
    for c in complaints:
        by_issue[f"{c.issue}|{c.sub_issue}"].append(c)
    strata = list(by_issue.values())
    for s in strata:
        rng.shuffle(s)
    out: list[Complaint] = []
    while len(out) < n and any(strata):  # round-robin across strata
        for s in strata:
            if s and len(out) < n:
                out.append(s.pop())
    return out


def write_labeling_sheet(sample: list[Complaint], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["complaint_id", "issue", "sub_issue", "narrative", "gold_root_cause", "gold_priority",
                    "labeler", "notes"])
        for c in sample:
            w.writerow([c.complaint_id, c.issue, c.sub_issue, c.narrative, "", "", "", ""])
