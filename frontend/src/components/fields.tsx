import clsx from "clsx";
import type { ReactNode } from "react";

/** Label + control + hint (the Input page's "Comments" column). */
export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="field-label">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

/** Yes / No toggle (the sheet's Yes/No ComboBoxes). */
export function YesNo({
  value,
  onChange,
  disabled = false,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div
      className={clsx(
        "flex overflow-hidden rounded border border-slate-300",
        disabled && "opacity-50",
      )}
    >
      {(["Yes", "No"] as const).map((opt) => (
        <button
          key={opt}
          type="button"
          disabled={disabled}
          className={clsx(
            "flex-1 px-3 py-1.5 text-sm font-semibold transition",
            value === (opt === "Yes")
              ? "bg-cyte-navy text-white"
              : "bg-white text-slate-600 hover:bg-cyte-panel",
          )}
          onClick={() => onChange(opt === "Yes")}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

/**
 * Numeric input. `scale=100` edits a fraction as a percentage (0.078 <-> 7.8).
 * `nullable` renders "Not Applicable" when disabled or when the value is null.
 */
export function NumberField({
  value,
  onChange,
  scale = 1,
  step,
  disabled = false,
  nullable = false,
  suffix,
  placeholder,
  readOnly = false,
}: {
  value: number | null | undefined;
  onChange: (v: number | null) => void;
  scale?: number;
  step?: number;
  disabled?: boolean;
  nullable?: boolean;
  suffix?: string;
  placeholder?: string;
  readOnly?: boolean;
}) {
  if (disabled && nullable) {
    return (
      <input className="field-input bg-slate-100 text-slate-500" value="Not Applicable" readOnly />
    );
  }
  const shown = value === null || value === undefined ? "" : String(round(value * scale));
  return (
    <div className="relative">
      <input
        type="number"
        step={step ?? (scale === 100 ? 0.01 : "any")}
        className={clsx("field-input", (disabled || readOnly) && "bg-slate-100 text-slate-600")}
        value={shown}
        placeholder={placeholder}
        disabled={disabled}
        readOnly={readOnly}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") return onChange(nullable ? null : 0);
          const n = Number(raw);
          if (!Number.isNaN(n)) onChange(n / scale);
        }}
      />
      {suffix && (
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400">
          {suffix}
        </span>
      )}
    </div>
  );
}

function round(v: number): number {
  return Math.round(v * 1e10) / 1e10;
}

export function ReadOnly({ value }: { value: string }) {
  return <input className="field-input bg-slate-100 text-slate-600" value={value} readOnly />;
}

export function Select<T extends string>({
  value,
  onChange,
  options,
  disabled = false,
  allowEmpty = false,
}: {
  value: T | "";
  onChange: (v: T) => void;
  options: readonly T[] | T[];
  disabled?: boolean;
  allowEmpty?: boolean;
}) {
  return (
    <select
      className={clsx("field-input", disabled && "bg-slate-100 text-slate-500")}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value as T)}
    >
      {allowEmpty && <option value="">—</option>}
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
