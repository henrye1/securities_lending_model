import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Batch, type Transaction } from "../lib/api";
import { pct } from "../lib/format";
import { GradeChip, StatusChip } from "../components/GradeChip";

export function BatchDetail() {
  const { batchId = "" } = useParams();
  const [batch, setBatch] = useState<Batch | null>(null);
  const [rows, setRows] = useState<Transaction[]>([]);
  const [error, setError] = useState("");

  const refresh = () => {
    api.getBatch(batchId).then(setBatch).catch((e) => setError(String(e.message ?? e)));
    api
      .listTransactions(batchId)
      .then(setRows)
      .catch((e) => setError(String(e.message ?? e)));
  };
  useEffect(refresh, [batchId]);

  return (
    <div>
      <div className="mb-1 text-xs text-slate-500">
        <Link to="/batches" className="hover:underline">
          Batches
        </Link>{" "}
        / {batch?.name ?? "…"}
      </div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-cyte-navyDark">{batch?.name ?? "Batch"}</h1>
        <Link className="btn-primary" to={`/batches/${batchId}/transactions/new`}>
          Add Transaction
        </Link>
      </div>
      {error && <div className="error-banner mb-4">{error}</div>}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-head">Client / Borrower</th>
              <th className="table-head">CIF</th>
              <th className="table-head">Reference Share</th>
              <th className="table-head">Structure</th>
              <th className="table-head">Status</th>
              <th className="table-head">PD</th>
              <th className="table-head">Risk Grade</th>
              <th className="table-head">Downturn LGD</th>
              <th className="table-head">EL</th>
              <th className="table-head w-52">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td className="table-cell text-slate-500" colSpan={10}>
                  No transactions in this batch yet.
                </td>
              </tr>
            )}
            {rows.map((tx) => (
              <tr key={tx.id} className="hover:bg-cyte-panel/40">
                <td className="table-cell font-medium">{tx.client_name}</td>
                <td className="table-cell">{tx.client_cif}</td>
                <td className="table-cell">
                  {tx.portfolio_of_shares ? "Portfolio of shares" : tx.reference_name}
                </td>
                <td className="table-cell">{tx.structure}</td>
                <td className="table-cell">
                  <StatusChip status={tx.status} />
                </td>
                <td className="table-cell">{tx.latest_pd == null ? "—" : pct(tx.latest_pd, 3)}</td>
                <td className="table-cell">
                  <GradeChip grade={tx.latest_risk_grade} />
                </td>
                <td className="table-cell">{tx.latest_lgd == null ? "—" : pct(tx.latest_lgd)}</td>
                <td className="table-cell">{tx.latest_el == null ? "—" : pct(tx.latest_el, 3)}</td>
                <td className="table-cell">
                  <Link className="btn-ghost" to={`/transactions/${tx.id}`}>
                    View
                  </Link>
                  {tx.latest_run_id && (
                    <a className="btn-ghost" href={api.exportUrl(tx.latest_run_id)}>
                      Export
                    </a>
                  )}
                  <button
                    className="btn-ghost text-cyte-ragRed"
                    onClick={async () => {
                      if (confirm(`Remove ${tx.client_name} from the batch?`)) {
                        await api.deleteTransaction(tx.id);
                        refresh();
                      }
                    }}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
