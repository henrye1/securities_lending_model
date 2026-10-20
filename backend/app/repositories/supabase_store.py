"""Supabase-backed Store implementation.

Tables (see supabase/migrations/0001_init.sql):
  batches(id, name, created_at)
  transactions(id, batch_id, payload jsonb, created_at, updated_at)
  runs(id, transaction_id, payload jsonb, created_at)

The document payloads reuse the pydantic schemas verbatim, so the JSON store
and the Postgres store are interchangeable. Untested against a live project
in this repo (no credentials); the shape mirrors the sibling suite apps.
"""
from __future__ import annotations

from supabase import Client, create_client

from app.core.settings import get_settings
from app.repositories.store import new_id, now
from app.schemas.models import Batch, Run, Transaction


class SupabaseStore:
    def __init__(self, client: Client | None = None):
        if client is None:
            s = get_settings()
            client = create_client(s.supabase_url, s.supabase_service_role_key)
        self.db = client

    # -- batches -----------------------------------------------------------
    def _count(self, batch_id: str) -> int:
        return (
            self.db.table("transactions").select("id", count="exact").eq("batch_id", batch_id)
            .execute().count or 0
        )

    def create_batch(self, name: str) -> Batch:
        batch = Batch(id=new_id(), name=name, created_at=now())
        self.db.table("batches").insert(
            {"id": batch.id, "name": batch.name, "created_at": batch.created_at.isoformat()}
        ).execute()
        return batch

    def list_batches(self) -> list[Batch]:
        rows = self.db.table("batches").select("*").order("created_at", desc=True).execute().data
        return [Batch(**r, transaction_count=self._count(r["id"])) for r in rows]

    def get_batch(self, batch_id: str) -> Batch | None:
        rows = self.db.table("batches").select("*").eq("id", batch_id).execute().data
        if not rows:
            return None
        return Batch(**rows[0], transaction_count=self._count(batch_id))

    def delete_batch(self, batch_id: str) -> None:
        self.db.table("batches").delete().eq("id", batch_id).execute()

    # -- transactions --------------------------------------------------------
    @staticmethod
    def _tx_row(tx: Transaction) -> dict:
        return {
            "id": tx.id,
            "batch_id": tx.batch_id,
            "payload": tx.model_dump(mode="json"),
            "created_at": tx.created_at.isoformat(),
            "updated_at": tx.updated_at.isoformat(),
        }

    def create_transaction(self, tx: Transaction) -> Transaction:
        self.db.table("transactions").insert(self._tx_row(tx)).execute()
        return tx

    def update_transaction(self, tx: Transaction) -> Transaction:
        self.db.table("transactions").update(self._tx_row(tx)).eq("id", tx.id).execute()
        return tx

    def get_transaction(self, tx_id: str) -> Transaction | None:
        rows = self.db.table("transactions").select("payload").eq("id", tx_id).execute().data
        return Transaction.model_validate(rows[0]["payload"]) if rows else None

    def list_transactions(self, batch_id: str) -> list[Transaction]:
        rows = (
            self.db.table("transactions").select("payload").eq("batch_id", batch_id)
            .order("created_at").execute().data
        )
        return [Transaction.model_validate(r["payload"]) for r in rows]

    def delete_transaction(self, tx_id: str) -> None:
        self.db.table("transactions").delete().eq("id", tx_id).execute()

    # -- runs ----------------------------------------------------------------
    def save_run(self, run: Run) -> Run:
        self.db.table("runs").upsert(
            {
                "id": run.id,
                "transaction_id": run.transaction_id,
                "payload": run.model_dump(mode="json"),
                "created_at": run.created_at.isoformat(),
            }
        ).execute()
        return run

    def get_run(self, run_id: str) -> Run | None:
        rows = self.db.table("runs").select("payload").eq("id", run_id).execute().data
        return Run.model_validate(rows[0]["payload"]) if rows else None

    def list_runs(self, transaction_id: str) -> list[Run]:
        rows = (
            self.db.table("runs").select("payload").eq("transaction_id", transaction_id)
            .order("created_at", desc=True).execute().data
        )
        return [Run.model_validate(r["payload"]) for r in rows]
