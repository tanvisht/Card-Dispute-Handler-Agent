"""Command line entry point:  `triage <command>`  (or `python -m dispute_triage.cli`)."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .classify import get_classifier
from .config import get_settings
from .evaluation.evaluate import evaluate, load_gold, to_markdown
from .evaluation.sampling import stratified_sample, write_labeling_sheet
from .ingest import cfpb
from .pipeline import classify_batch, run
from .storage import get_repository


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="triage")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="download complaints from the CFPB API to JSONL")
    f.add_argument("--limit", type=int, default=5000)
    f.add_argument("--since", default="2023-01-01")
    f.add_argument("--until")
    f.add_argument("--csv", help="read from a CFPB bulk complaints.csv instead of the API")
    f.add_argument("--out", default="data/raw/complaints.jsonl")

    r = sub.add_parser("run", help="load + classify a JSONL file into the configured store")
    r.add_argument("--input", default="data/raw/complaints.jsonl")
    r.add_argument("--workers", type=int, default=8)

    s = sub.add_parser("sample", help="create a stratified labeling sheet")
    s.add_argument("--input", default="data/raw/complaints.jsonl")
    s.add_argument("-n", type=int, default=300)
    s.add_argument("--out", default="data/labels/to_label.csv")

    e = sub.add_parser("evaluate", help="classify the gold set and score against acceptance criteria")
    e.add_argument("--input", default="data/raw/complaints.jsonl")
    e.add_argument("--gold", default="data/labels/gold_labels.csv")
    e.add_argument("--out", default="reports/eval")
    e.add_argument("--workers", type=int, default=8)

    k = sub.add_parser("agreement", help="Cohen's kappa between two labelers on a double-labeled sheet")
    k.add_argument("--sheet", default="data/labels/double_labeled.csv")
    k.add_argument("--field", choices=["root_cause", "priority"], default="root_cause")

    a = p.parse_args(argv)
    if a.cmd == "fetch":
        src = cfpb.read_csv(a.csv, a.limit) if a.csv else cfpb.fetch_from_api(a.limit, a.since, a.until)
        print(f"wrote {cfpb.write_jsonl(src, a.out)} complaints -> {a.out}")
    elif a.cmd == "run":
        print(json.dumps(run(get_repository(), get_classifier(), cfpb.read_jsonl(a.input), a.workers), indent=2))
    elif a.cmd == "sample":
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        write_labeling_sheet(stratified_sample(cfpb.read_jsonl(a.input), a.n), a.out)
        print(f"labeling sheet -> {a.out}")
    elif a.cmd == "evaluate":
        gold = load_gold(a.gold)
        complaints = [c for c in cfpb.read_jsonl(a.input) if c.complaint_id in gold]
        preds, errors = classify_batch(get_classifier(), complaints, a.workers)
        rep = evaluate(preds, gold)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out + ".json").write_text(rep.to_json())
        Path(a.out + ".md").write_text(to_markdown(rep))
        print(to_markdown(rep))
        print(f"classifier={get_settings().triage_classifier} errors={len(errors)}")
        return 0 if rep.passed else 1
    elif a.cmd == "agreement":
        from .evaluation.agreement import agreement_from_csv
        print(json.dumps(agreement_from_csv(a.sheet, a.field), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
