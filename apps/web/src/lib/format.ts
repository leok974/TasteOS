

/**
 * Formats duration minutes into a human-readable pill string.
 * Examples:
 * - < 60 min -> "45m"
 * - = 60 min -> "1H"
 * - > 60 min -> "1H30" (2-digit minutes)
 * 
 * Returns null if the value is invalid.
 */
export function formatDurationPill(
  value: unknown,
  opts?: { estimated?: boolean }
): string | null {
  if (value === null || value === undefined) return null;

  const n =
    typeof value === "number"
      ? value
      : typeof value === "string"
        ? parseInt(value, 10)
        : NaN;

  if (!Number.isFinite(n) || n <= 0) return null;

  const minutes = Math.round(n); // keep deterministic
  const prefix = opts?.estimated ? "~" : "";

  if (minutes < 60) return `${prefix}${minutes}m`;

  const h = Math.floor(minutes / 60);
  const m = minutes % 60;

  if (m === 0) return `${prefix}${h}H`;
  return `${prefix}${h}H${String(m).padStart(2, "0")}`;
}

export const formatMinutes = (value: unknown) => formatDurationPill(value);

