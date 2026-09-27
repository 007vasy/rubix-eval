"""Persistent records of visual / computer-use solve attempts."""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import repo_root


def solves_dir() -> Path:
    env = os.environ.get("RUBIX_SOLVES_DIR")
    if env:
        return Path(env)
    return repo_root() / "solves"


def record_path(record_id: str) -> Path:
    return solves_dir() / f"{record_id}.json"


def record_lane(session: dict[str, Any] | None = None) -> str:
    raw = (session or {}).get("lane") or os.environ.get("RUBIX_LANE") or "open"
    lane = str(raw).strip().lower()
    return "verified" if lane == "verified" else "open"


def make_record(
    session: dict[str, Any],
    verified: dict[str, Any],
    algorithms: list[dict[str, Any]],
    optimality: dict[str, Any],
    *,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    record_id = f"{stamp}-{session['id']}"
    lane = record_lane(session)
    web_access = lane != "verified"
    if session.get("web_access") is not None:
        web_access = bool(session.get("web_access"))
    harness = session.get("harness") or os.environ.get("RUBIX_HARNESS") or (
        "inspect" if lane == "verified" else "browser"
    )
    return {
        "record_id": record_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session["id"],
        "kind": session["kind"],
        "size": session["size"],
        "scramble_depth": session["scramble_depth"],
        "seed": session["seed"],
        "max_moves": session["max_moves"],
        "challenge_id": session.get("challenge_id"),
        "depth_label": session.get("depth_label"),
        "ai": verified.get("ai") or session.get("ai") or "unspecified AI",
        "state": session["state"],
        "lane": lane,
        "web_access": web_access,
        "harness": str(harness)[:32],
        "attested": lane == "verified",
        "attempt": verified,
        "client": {
            "solved": (progress or {}).get("solved"),
            "htm": (progress or {}).get("htm"),
            "qtm": (progress or {}).get("qtm"),
            "misplaced": (progress or {}).get("misplaced"),
        },
        "algorithms": algorithms,
        "optimality": optimality,
    }


def solves_bucket_name() -> str | None:
    name = (os.environ.get("RUBIX_SOLVES_BUCKET") or "").strip()
    return name or None


def blob_name_for(record: dict[str, Any]) -> str:
    lane = "verified" if (record.get("lane") or "open") == "verified" else "open"
    return f"{lane}/{record['record_id']}.json"


def _gcs_bucket():
    name = solves_bucket_name()
    if not name:
        return None
    from google.cloud import storage  # type: ignore

    return storage.Client().bucket(name)


# Bucket reads are cached in-process: one listing per TTL, and a record is only downloaded
# again when its generation changes. Every board is built from this, so page loads stay fast.
BUCKET_TTL_SEC = float(os.environ.get("RUBIX_BUCKET_TTL", "30"))
_bucket_lock = threading.Lock()
_bucket_cache: dict[str, Any] = {"bucket": None, "listed_at": None, "records": {}}


def _is_record_blob(name: str) -> bool:
    return name.endswith(".json") and not name.endswith(("solves.jsonl", "algorithm_bench.json"))


def _bucket_records(bucket) -> dict[str, dict[str, Any]]:
    """blob name -> record, refreshed from the bucket at most once per TTL."""
    now = time.monotonic()
    with _bucket_lock:
        cache = _bucket_cache
        if cache["bucket"] != bucket.name:
            cache.update(bucket=bucket.name, listed_at=None, records={})
        fresh = cache["listed_at"] is not None and now - cache["listed_at"] < BUCKET_TTL_SEC
        if fresh:
            return {name: data for name, (_gen, data) in cache["records"].items()}
        known = dict(cache["records"])
    blobs = [b for b in bucket.list_blobs() if _is_record_blob(b.name)]
    stale = [b for b in blobs if known.get(b.name, (None, None))[0] != b.generation]

    def fetch(blob):
        try:
            return blob.name, blob.generation, json.loads(blob.download_as_text())
        except (json.JSONDecodeError, OSError, ValueError):
            return blob.name, blob.generation, None

    fetched = {}
    if stale:
        with ThreadPoolExecutor(max_workers=min(16, len(stale))) as pool:
            for name, gen, data in pool.map(fetch, stale):
                if data is not None:
                    fetched[name] = (gen, data)
    live = {b.name for b in blobs}
    with _bucket_lock:
        records = {name: entry for name, entry in known.items() if name in live}
        records.update(fetched)
        _bucket_cache.update(listed_at=time.monotonic(), records=records)
        return {name: data for name, (_gen, data) in records.items()}


def _remember_blob(bucket_name: str, name: str, generation: Any, record: dict[str, Any]) -> None:
    with _bucket_lock:
        if _bucket_cache["bucket"] == bucket_name:
            _bucket_cache["records"][name] = (generation, record)


def write_record(record: dict[str, Any], directory: Path | None = None) -> Path:
    payload = json.dumps(record, indent=2) + "\n"
    bucket = _gcs_bucket() if directory is None else None
    if bucket is not None:
        blob = bucket.blob(blob_name_for(record))
        blob.upload_from_string(payload, content_type="application/json")
        _remember_blob(bucket.name, blob.name, getattr(blob, "generation", None), json.loads(payload))
        return Path(f"gs://{bucket.name}/{blob.name}")
    root = directory or solves_dir()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{record['record_id']}.json"
    path.write_text(payload, encoding="utf-8")
    log = root / "solves.jsonl"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    return path


def load_record(record_id: str, directory: Path | None = None) -> dict[str, Any] | None:
    bucket = _gcs_bucket() if directory is None else None
    if bucket is not None:
        records = _bucket_records(bucket)
        for prefix in ("verified/", "open/"):
            if f"{prefix}{record_id}.json" in records:
                return records[f"{prefix}{record_id}.json"]
        for name, data in records.items():
            if record_id in name:
                return data
        return None
    root = directory or solves_dir()
    path = root / f"{record_id}.json"
    if not path.exists():
        matches = sorted(root.glob(f"*{record_id}*.json"))
        if not matches:
            return None
        path = matches[-1]
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_row(data: dict[str, Any], fallback_id: str = "") -> dict[str, Any] | None:
    if not data.get("record_id") and not data.get("session_id"):
        return None
    opt = data.get("optimality") or {}
    att = data.get("attempt") or {}
    return {
        "record_id": data.get("record_id") or fallback_id,
        "recorded_at": data.get("recorded_at"),
        "session_id": data.get("session_id"),
        "kind": data.get("kind"),
        "size": data.get("size"),
        "ndim": data.get("ndim") or (data.get("state") or {}).get("ndim"),
        "scramble_depth": data.get("scramble_depth"),
        "challenge_id": data.get("challenge_id"),
        "depth_label": data.get("depth_label"),
        "ai": data.get("ai") or att.get("ai"),
        "solved": att.get("solved"),
        "ai_htm": att.get("htm"),
        "elapsed_sec": att.get("elapsed_sec"),
        "click_count": att.get("click_count"),
        "step_count": att.get("step_count") if att.get("step_count") is not None else att.get("move_count"),
        "tokens_used": att.get("tokens_used"),
        "token_cost_usd": att.get("token_cost_usd"),
        "has_replay": bool(att.get("history") or att.get("moves") or att.get("clicks")),
        "best_htm": opt.get("best_htm"),
        "best_algorithm": opt.get("best_algorithm"),
        "optimality_ratio": opt.get("optimality_ratio"),
        "excess_vs_best": opt.get("excess_vs_best"),
        "optimal": opt.get("optimal"),
        "lane": data.get("lane") or "open",
        "web_access": data.get("web_access") if data.get("web_access") is not None else data.get("lane") != "verified",
        "harness": data.get("harness") or "browser",
        "attested": bool(data.get("attested")),
    }


def list_records(directory: Path | None = None, *, limit: int = 200) -> list[dict[str, Any]]:
    bucket = _gcs_bucket() if directory is None else None
    rows: list[dict[str, Any]] = []
    if bucket is not None:
        records = _bucket_records(bucket)
        # Newest first across both lanes (record ids start with a timestamp).
        for name in sorted(records, key=lambda n: Path(n).stem, reverse=True):
            row = _summary_row(records[name], Path(name).stem)
            if row:
                rows.append(row)
            if len(rows) >= limit:
                break
        return rows
    root = directory or solves_dir()
    if not root.exists():
        return []
    files = sorted(root.glob("*.json"), reverse=True)
    for path in files[:limit]:
        if path.name in ("solves.jsonl", "algorithm_bench.json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        row = _summary_row(data, path.stem)
        if row:
            rows.append(row)
    return rows


def publish_verified(record_id: str, directory: Path | None = None) -> dict[str, Any]:
    """Attest an offline verified run. Refuses open / web-on records."""
    rec = load_record(record_id, directory)
    if not rec:
        raise FileNotFoundError(record_id)
    lane = rec.get("lane") or "open"
    web_access = rec.get("web_access")
    if web_access is None:
        web_access = lane != "verified"
    if lane != "verified" or web_access:
        raise ValueError(
            f"refusing to attest {record_id}: lane={lane!r} web_access={web_access!r} "
            "(verified runs must be created offline with RUBIX_LANE=verified)"
        )
    rec["lane"] = "verified"
    rec["web_access"] = False
    rec["attested"] = True
    rec["harness"] = rec.get("harness") if rec.get("harness") not in (None, "browser") else "openshell"
    write_record(rec, directory)
    return rec


def public_record(record: dict[str, Any]) -> dict[str, Any]:
    """Harness view: no withheld scramble sequence."""
    out = dict(record)
    out.pop("oracle", None)
    return out
