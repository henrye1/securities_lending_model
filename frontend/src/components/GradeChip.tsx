import clsx from "clsx";

/** RAG colouring for the SB01-SB25 master scale: SB01-10 green, SB11-17 amber, SB18+ / D red. */
export function GradeChip({ grade }: { grade: string | null | undefined }) {
  if (!grade) return <span>—</span>;
  const num = grade.startsWith("SB") ? parseInt(grade.slice(2), 10) : 99;
  const band = grade.startsWith("D") || num >= 18 ? "red" : num >= 11 ? "amber" : "green";
  return (
    <span
      className={clsx(
        "inline-block rounded px-2 py-0.5 text-xs font-bold",
        band === "green" && "bg-cyte-ragGreenBg text-cyte-ragGreen",
        band === "amber" && "bg-cyte-ragAmberBg text-cyte-ragAmber",
        band === "red" && "bg-cyte-ragRedBg text-cyte-ragRed",
      )}
    >
      {grade}
    </span>
  );
}

export function StatusChip({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-block rounded px-2 py-0.5 text-xs font-bold capitalize",
        status === "calculated" && "bg-cyte-ragGreenBg text-cyte-ragGreen",
        status === "draft" && "bg-slate-200 text-slate-600",
      )}
    >
      {status}
    </span>
  );
}
