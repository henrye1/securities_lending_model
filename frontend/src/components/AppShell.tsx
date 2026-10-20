import { type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const inCalculator =
    location.pathname.startsWith("/batches") || location.pathname.startsWith("/transactions");
  return (
    <div className="flex min-h-full flex-col">
      <header className="bg-cyte-navy text-white shadow-md print:hidden">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-baseline gap-2">
            <span className="text-lg font-bold tracking-widest">CYTE</span>
            <span className="text-sm font-light uppercase tracking-[0.3em] text-cyte-lavender">
              Risk Suite
            </span>
          </Link>
          <nav className="flex items-center gap-6 text-sm">
            <Link
              to="/"
              className={
                location.pathname === "/" ? "font-semibold" : "text-cyte-lavender hover:text-white"
              }
            >
              Suite Home
            </Link>
            <Link
              to="/batches"
              className={inCalculator ? "font-semibold" : "text-cyte-lavender hover:text-white"}
            >
              Securities Lending Calculator
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-6 print:max-w-none print:px-0 print:py-0">
        {children}
      </main>
      <footer className="border-t border-slate-300 bg-white px-6 py-2 text-center text-xs text-slate-500 print:hidden">
        CYTE Risk Suite — Securities Lending (Share Cover) Model · PD, LGD, EL &amp; RWA for
        share-backed lending
      </footer>
    </div>
  );
}
