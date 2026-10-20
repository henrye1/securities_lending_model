import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Batch } from "../lib/api";

export function Batches() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const refresh = () =>
    api.listBatches().then(setBatches).catch((e) => setError(String(e.message ?? e)));
  useEffect(() => {
    refresh();
  }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      await api.createBatch(name.trim());
      setName("");
      refresh();
    } catch (e) {
      setError(String((e as Error).message));
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-cyte-navyDark">Securities Lending Calculator</h1>
          <p className="text-sm text-slate-600">
            Create a batch, capture share-cover transactions on the Input page, then calculate PD,
            LGD, EL and RWA%.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            className="field-input w-64"
            placeholder="New batch name…"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && create()}
          />
          <button className="btn-primary" onClick={create} disabled={!name.trim()}>
            Create New Batch
          </button>
        </div>
      </div>
      {error && <div className="error-banner mb-4">{error}</div>}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-head">Batch</th>
              <th className="table-head">Created</th>
              <th className="table-head">Transactions</th>
              <th className="table-head w-40">Actions</th>
            </tr>
          </thead>
          <tbody>
            {batches.length === 0 && (
              <tr>
                <td className="table-cell text-slate-500" colSpan={4}>
                  No batches yet — create one to begin.
                </td>
              </tr>
            )}
            {batches.map((b) => (
              <tr key={b.id} className="hover:bg-cyte-panel/40">
                <td className="table-cell font-medium">
                  <Link className="text-cyte-navy hover:underline" to={`/batches/${b.id}`}>
                    {b.name}
                  </Link>
                </td>
                <td className="table-cell">{new Date(b.created_at).toLocaleDateString()}</td>
                <td className="table-cell">{b.transaction_count}</td>
                <td className="table-cell">
                  <Link className="btn-ghost" to={`/batches/${b.id}`}>
                    Open
                  </Link>
                  <button
                    className="btn-ghost text-cyte-ragRed"
                    onClick={async () => {
                      if (confirm(`Delete batch "${b.name}" and its contents?`)) {
                        await api.deleteBatch(b.id);
                        refresh();
                      }
                    }}
                  >
                    Delete
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
