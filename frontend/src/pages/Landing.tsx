import { Link } from "react-router-dom";

const tools = [
  {
    name: "Securities Lending Calculator",
    description:
      "Capture a share-backed lending transaction exactly as on the model's Input page — " +
      "client, loan structure, pledged shares, default cover ratio, interest, dividends and the " +
      "reference entity — then run the 10,000-path share-cover simulation.",
    to: "/batches",
    active: true,
  },
  {
    name: "Portfolio of Shares",
    description:
      "When the pledge is a basket of up to ten stocks, capture each stock, the equity and " +
      "currency correlation matrices and let the model combine them into the value-weighted " +
      "price, volatility, yield and unwind period that feed the calculation.",
    to: "/batches",
    active: true,
  },
  {
    name: "Share Cover Risk Report",
    description:
      "The Print Report & Results page: PD, risk grade, downturn LGD, expected loss, EL grade " +
      "and RWA% for the Reference Entity, the Client/Borrower and the Combined exposure, with " +
      "print view and CYTE-branded Excel export.",
    to: "/batches",
    active: true,
  },
];

export function Landing() {
  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-cyte-navyDark">Risk Suite</h1>
      <p className="mb-6 text-sm text-slate-600">
        The Securities Lending (Share Cover) Model estimates the Probability of Default, Loss Given
        Default, Expected Loss and RWA% of loans secured by pledged shares. It follows the Stock
        Lending Model workbook step by step — Input, Portfolio Transactions, Calculations, Print
        Report &amp; Results — simulating the share price over the life of the loan against the
        default cover ratio covenant and the issuer's own default risk.
      </p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {tools.map((tool) => (
          <Link
            key={tool.name}
            to={tool.to}
            className={
              "card block p-5 transition " +
              (tool.active
                ? "hover:-translate-y-0.5 hover:border-cyte-navy hover:shadow-md"
                : "cursor-not-allowed opacity-50")
            }
            onClick={(e) => !tool.active && e.preventDefault()}
          >
            <div className="mb-2 h-1.5 w-10 rounded bg-cyte-navy" />
            <h2 className="mb-1 font-semibold text-cyte-navyDark">{tool.name}</h2>
            <p className="text-sm text-slate-600">{tool.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
