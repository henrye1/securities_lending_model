"""API routes - mirrors the suite siblings' endpoint surface:
batches -> transactions -> calculate -> runs -> export."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.domain import reference
from app.repositories.store import Store, new_id, now
from app.schemas.models import Batch, Run, Transaction, TransactionCreate
from app.services import calc_service

router = APIRouter(prefix="/api")


def get_store(request: Request) -> Store:
    return request.app.state.store


class BatchCreate(BaseModel):
    name: str


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "model": "securities-lending-model"}


@router.get("/reference/capture-config")
def capture_config() -> dict:
    lists = reference.capture_lists()
    return {
        "structures": lists["structures"],
        "yes_no": lists["yes_no"],
        "listings": lists["listings"],
        "dividend_options": lists["dividend_options"],
        "recovery_policies": lists["recovery_policies"],
        "grades": lists["grades"],
        "revenue_sizes": lists["revenue_sizes"],
        "sectors": reference.sectors(),
        "countries": [
            {"name": c["name"], "risk_free_rate": c["risk_free_rate"]} for c in reference.countries()
        ],
        "pd_masterscale": reference.pd_masterscale(),
        "defaults": {
            "default_cover_ratio": 1.75,
            "unlisted_haircut": 0.5,
            "illiquid_haircut": 0.3,
            "min_pd": lists["min_pd"],
            "trading_days": lists["trading_days"],
            "unwind_pct": lists["unwind_pct"],
        },
    }


# ---- batches ---------------------------------------------------------------

@router.post("/batches", response_model=Batch)
def create_batch(body: BatchCreate, store: Store = Depends(get_store)) -> Batch:
    if not body.name.strip():
        raise HTTPException(422, "Batch name is required")
    return store.create_batch(body.name.strip())


@router.get("/batches", response_model=list[Batch])
def list_batches(store: Store = Depends(get_store)) -> list[Batch]:
    return store.list_batches()


@router.get("/batches/{batch_id}", response_model=Batch)
def get_batch(batch_id: str, store: Store = Depends(get_store)) -> Batch:
    batch = store.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")
    return batch


@router.delete("/batches/{batch_id}", status_code=204)
def delete_batch(batch_id: str, store: Store = Depends(get_store)) -> Response:
    store.delete_batch(batch_id)
    return Response(status_code=204)


# ---- transactions ------------------------------------------------------------

@router.post("/batches/{batch_id}/transactions", response_model=Transaction)
def create_transaction(
    batch_id: str, body: TransactionCreate, store: Store = Depends(get_store)
) -> Transaction:
    if not store.get_batch(batch_id):
        raise HTTPException(404, "Batch not found")
    tx = Transaction(
        **body.model_dump(), id=new_id(), batch_id=batch_id, created_at=now(), updated_at=now()
    )
    return store.create_transaction(tx)


@router.get("/batches/{batch_id}/transactions", response_model=list[Transaction])
def list_transactions(batch_id: str, store: Store = Depends(get_store)) -> list[Transaction]:
    return store.list_transactions(batch_id)


def _get_tx(store: Store, tx_id: str) -> Transaction:
    tx = store.get_transaction(tx_id)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return tx


@router.get("/transactions/{tx_id}", response_model=Transaction)
def get_transaction(tx_id: str, store: Store = Depends(get_store)) -> Transaction:
    return _get_tx(store, tx_id)


@router.put("/transactions/{tx_id}", response_model=Transaction)
def update_transaction(
    tx_id: str, body: TransactionCreate, store: Store = Depends(get_store)
) -> Transaction:
    tx = _get_tx(store, tx_id)
    updated = tx.model_copy(update={**body.model_dump(), "updated_at": now()})
    return store.update_transaction(updated)


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: str, store: Store = Depends(get_store)) -> Response:
    store.delete_transaction(tx_id)
    return Response(status_code=204)


# ---- runs ---------------------------------------------------------------------

@router.post("/transactions/{tx_id}/calculate", response_model=Run)
def calculate(tx_id: str, store: Store = Depends(get_store)) -> Run:
    tx = _get_tx(store, tx_id)
    try:
        return calc_service.calculate(store, tx)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/transactions/{tx_id}/runs", response_model=list[Run])
def list_runs(tx_id: str, store: Store = Depends(get_store)) -> list[Run]:
    return store.list_runs(tx_id)


def _get_run(store: Store, run_id: str) -> Run:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/runs/{run_id}", response_model=Run)
def get_run(run_id: str, store: Store = Depends(get_store)) -> Run:
    return _get_run(store, run_id)


@router.get("/runs/{run_id}/export.xlsx")
def export_xlsx(run_id: str, store: Store = Depends(get_store)) -> Response:
    from app.services.export_xlsx import export_run

    run = _get_run(store, run_id)
    tx = _get_tx(store, run.transaction_id)
    filename, payload = export_run(tx, run)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
