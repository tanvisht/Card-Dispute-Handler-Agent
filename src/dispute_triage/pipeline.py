"""Batch pipeline: classify complaints concurrently and persist results."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .classify import Classifier
from .models import Classification, Complaint
from .storage import Repository

log = logging.getLogger(__name__)


def classify_batch(classifier: Classifier, complaints: list[Complaint], workers: int = 8
                   ) -> tuple[list[Classification], list[tuple[str, str]]]:
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(classifier.classify, c): c.complaint_id for c in complaints}
        for i, fut in enumerate(as_completed(futs), 1):
            cid = futs[fut]
            try:
                results.append(fut.result())
            except Exception as e:  # one bad record must not kill the batch
                log.exception("classification failed for %s", cid)
                errors.append((cid, repr(e)))
            if i % 250 == 0:
                log.info("classified %d/%d", i, len(complaints))
    return results, errors


def run(repo: Repository, classifier: Classifier, complaints: list[Complaint],
        workers: int = 8, chunk: int = 500) -> dict:
    repo.upsert_complaints(complaints)
    todo = set(repo.unclassified_ids())
    pending = [c for c in complaints if c.complaint_id in todo]
    total, errs = 0, []
    for i in range(0, len(pending), chunk):  # persist in chunks -> resumable
        res, e = classify_batch(classifier, pending[i:i + chunk], workers)
        total += repo.insert_classifications(res) if res else 0
        errs += e
    return {"loaded": len(complaints), "classified": total, "skipped_already_done": len(complaints) - len(pending),
            "errors": len(errs)}
