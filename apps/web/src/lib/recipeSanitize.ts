export function cleanTitle(raw: string | null | undefined): string {
  const s = (raw ?? "").trim();
  // remove leading markdown heading like "# " / "## " / "### "
  let out = s.replace(/^\s*#{1,6}\s+/, "").trim();
  // remove bold markers
  out = out.replace(/\*\*/g, "");
  return out;
}

export function cleanLine(raw: string | null | undefined): string {
  let s = (raw ?? "").trim();

  // remove common inline markdown emphasis
  s = s.replace(/\*\*/g, ""); // **bold**
  s = s.replace(/__/g, "");   // __bold__

  // remove leading bullet markers (common when models output lists)
  s = s.replace(/^\s*[-*]\s+/, "");

  // remove leading markdown headings inside text blocks
  s = s.replace(/^\s*#{1,6}\s+/, "");

  return s.trim();
}

export function cleanSteps(steps: Array<string> | null | undefined): Array<string> {
  return (steps ?? []).map(cleanLine).filter(Boolean);
}
