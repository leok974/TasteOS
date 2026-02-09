
/**
 * Formats minutes into a readable string "Xm".
 * Returns null if the value is invalid (null, undefined, 0, non-finite).
 */
export function formatMinutes(value: unknown): string | null {
  if (value === null || value === undefined) return null;

  const n =
    typeof value === "number" ? value :
    typeof value === "string" ? parseInt(value, 10) :
    NaN;

  if (!Number.isFinite(n) || n <= 0) return null;
  return `${n}m`;
}
