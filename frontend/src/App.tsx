import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Landing } from "./pages/Landing";
import { Batches } from "./pages/Batches";
import { BatchDetail } from "./pages/BatchDetail";
import { TransactionWizard } from "./pages/TransactionWizard";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/batches" element={<Batches />} />
        <Route path="/batches/:batchId" element={<BatchDetail />} />
        <Route path="/batches/:batchId/transactions/new" element={<TransactionWizard />} />
        <Route path="/transactions/:txId" element={<TransactionWizard />} />
      </Routes>
    </AppShell>
  );
}
