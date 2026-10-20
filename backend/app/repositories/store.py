"""Persistence layer.

`Store` is the interface the services use. Two implementations:

- `MemoryStore` - dict-backed with optional JSON-file persistence; default when
  Supabase credentials are not configured (local dev, tests).
- `SupabaseStore` (supabase_store.py) - Postgres via supabase-py; selected
  automatically when SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are set.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.schemas.models import Batch, Run, Transaction


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class Store(Protocol):
    # batches
    def create_batch(self, name: str) -> Batch: ...
    def list_batches(self) -> list[Batch]: ...
    def get_batch(self, batch_id: str) -> Batch | None: ...
    def delete_batch(self, batch_id: str) -> None: ...
    # transactions
    def create_transaction(self, tx: Transaction) -> Transaction: ...
    def update_transaction(self, tx: Transaction) -> Transaction: ...
    def get_transaction(self, tx_id: str) -> Transaction | None: ...
    def list_transactions(self, batch_id: str) -> list[Transaction]: ...
    def delete_transaction(self, tx_id: str) -> None: ...
    # runs
    def save_run(self, run: Run) -> Run: ...
    def get_run(self, run_id: str) -> Run | None: ...
    def list_runs(self, transaction_id: str) -> list[Run]: ...


class MemoryStore:
    def __init__(self, persist_path: str | None = None):
        self._lock = threading.Lock()
        self._path = Path(persist_path) if persist_path else None
        self.batches: dict[str, Batch] = {}
        self.transactions: dict[str, Transaction] = {}
        self.runs: dict[str, Run] = {}
        if self._path and self._path.exists():
            self._load()

    # -- persistence -------------------------------------------------------
    def _load(self) -> None:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        self.batches = {k: Batch.model_validate(v) for k, v in raw.get("batches", {}).items()}
        self.transactions = {
            k: Transaction.model_validate(v) for k, v in raw.get("transactions", {}).items()
        }
        self.runs = {k: Run.model_validate(v) for k, v in raw.get("runs", {}).items()}

    def _flush(self) -> None:
        if not self._path:
            return
        payload = {
            "batches": {k: v.model_dump(mode="json") for k, v in self.batches.items()},
            "transactions": {k: v.model_dump(mode="json") for k, v in self.transactions.items()},
            "runs": {k: v.model_dump(mode="json") for k, v in self.runs.items()},
        }
        self._path.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    # -- batches -----------------------------------------------------------
    def create_batch(self, name: str) -> Batch:
        with self._lock:
            batch = Batch(id=new_id(), name=name, created_at=now())
            self.batches[batch.id] = batch
            self._flush()
            return batch

    def _with_count(self, b: Batch) -> Batch:
        count = sum(1 for t in self.transactions.values() if t.batch_id == b.id)
        return b.model_copy(update={"transaction_count": count})

    def list_batches(self) -> list[Batch]:
        return [
            self._with_count(b)
            for b in sorted(self.batches.values(), key=lambda x: x.created_at, reverse=True)
        ]

    def get_batch(self, batch_id: str) -> Batch | None:
        b = self.batches.get(batch_id)
        return self._with_count(b) if b else None

    def delete_batch(self, batch_id: str) -> None:
        with self._lock:
            self.batches.pop(batch_id, None)
            for tx_id in [k for k, t in self.transactions.items() if t.batch_id == batch_id]:
                self.transactions.pop(tx_id)
                for run_id in [k for k, r in self.runs.items() if r.transaction_id == tx_id]:
                    self.runs.pop(run_id)
            self._flush()

    # -- transactions --------------------------------------------------------
    def create_transaction(self, tx: Transaction) -> Transaction:
        with self._lock:
            self.transactions[tx.id] = tx
            self._flush()
            return tx

    def update_transaction(self, tx: Transaction) -> Transaction:
        with self._lock:
            self.transactions[tx.id] = tx
            self._flush()
            return tx

    def get_transaction(self, tx_id: str) -> Transaction | None:
        return self.transactions.get(tx_id)

    def list_transactions(self, batch_id: str) -> list[Transaction]:
        return sorted(
            (t for t in self.transactions.values() if t.batch_id == batch_id),
            key=lambda t: t.created_at,
        )

    def delete_transaction(self, tx_id: str) -> None:
        with self._lock:
            self.transactions.pop(tx_id, None)
            for run_id in [k for k, r in self.runs.items() if r.transaction_id == tx_id]:
                self.runs.pop(run_id)
            self._flush()

    # -- runs ----------------------------------------------------------------
    def save_run(self, run: Run) -> Run:
        with self._lock:
            self.runs[run.id] = run
            self._flush()
            return run

    def get_run(self, run_id: str) -> Run | None:
        return self.runs.get(run_id)

    def list_runs(self, transaction_id: str) -> list[Run]:
        return sorted(
            (r for r in self.runs.values() if r.transaction_id == transaction_id),
            key=lambda r: r.created_at,
            reverse=True,
        )
