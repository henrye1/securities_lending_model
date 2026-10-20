"""End-to-end API flow on the Excelcior golden case:
batch -> transaction -> calculate -> run -> export."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "golden_excelcior.json"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    from app.core.settings import get_settings
    get_settings.cache_clear()
    from app.repositories.store import MemoryStore
    app = create_app()
    app.state.store = MemoryStore(persist_path=str(tmp_path / "store.json"))
    with TestClient(app) as c:
        yield c


def _inputs() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["inputs"]


def test_capture_config(client):
    cfg = client.get("/api/reference/capture-config").json()
    assert len(cfg["countries"]) == 179 and len(cfg["grades"]) == 25
    assert cfg["structures"][0] == "Bullet Payment"
    assert cfg["defaults"]["default_cover_ratio"] == 1.75
    assert any(c["name"] == "South Africa" and c["risk_free_rate"] == 0.07 for c in cfg["countries"])


def test_full_flow(client):
    batch = client.post("/api/batches", json={"name": "Oct 2026"}).json()
    r = client.post(f"/api/batches/{batch['id']}/transactions", json=_inputs())
    assert r.status_code == 200, r.text
    tx = r.json()
    assert tx["status"] == "draft" and tx["client_name"] == "Excelcior Shipping"

    run = client.post(f"/api/transactions/{tx['id']}/calculate").json()
    assert run["pd_total"] == pytest.approx(0.052780683384851604, rel=1e-9)
    assert run["risk_grade"] == "SB19"
    assert run["result"]["report"]["combined"]["rwa_pct"] == pytest.approx(0.9020337553547401, rel=1e-9)
    assert run["result"]["derived"]["unwind_years"] == pytest.approx(4.555776892430279, rel=1e-12)
    assert run["result"]["derived"]["liquidity"] == "Illiquid"
    assert len(run["result"]["years"]) == 10

    tx2 = client.get(f"/api/transactions/{tx['id']}").json()
    assert tx2["status"] == "calculated" and tx2["latest_run_id"] == run["id"]
    assert tx2["latest_risk_grade"] == "SB19"
    assert client.get(f"/api/runs/{run['id']}").json()["id"] == run["id"]
    assert len(client.get(f"/api/transactions/{tx['id']}/runs").json()) == 1
    assert client.get(f"/api/batches/{batch['id']}").json()["transaction_count"] == 1


def test_validation_errors(client):
    batch = client.post("/api/batches", json={"name": "b"}).json()
    bad = _inputs() | {"maturity_date": "2015-05-31"}
    tx = client.post(f"/api/batches/{batch['id']}/transactions", json=bad).json()
    r = client.post(f"/api/transactions/{tx['id']}/calculate")
    assert r.status_code == 422 and "maturity" in r.text.lower()
    long = _inputs() | {"maturity_date": "2030-05-31"}
    tx = client.post(f"/api/batches/{batch['id']}/transactions", json=long).json()
    assert client.post(f"/api/transactions/{tx['id']}/calculate").status_code == 422


def test_portfolio_mode_uses_combined_values(client):
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    sheet = fx["portfolio_sheet"]
    payload = _inputs() | {
        "portfolio_of_shares": True,
        "portfolio": {"stocks": sheet["stocks"], "equity_correlation": sheet["equity_correlation"]},
    }
    batch = client.post("/api/batches", json={"name": "p"}).json()
    tx = client.post(f"/api/batches/{batch['id']}/transactions", json=payload).json()
    run = client.post(f"/api/transactions/{tx['id']}/calculate").json()
    port = run["result"]["portfolio"]
    assert port["stock_volatility"] == pytest.approx(sheet["combined"]["stock_volatility"], rel=1e-9)
    assert run["result"]["derived"]["volatility"] == pytest.approx(sheet["combined"]["stock_volatility"], rel=1e-9)
    assert run["result"]["derived"]["share_value"] == pytest.approx(
        sheet["combined"]["number_of_shares"] * sheet["combined"]["share_price"], rel=1e-9
    )
