"use client";

import * as React from "react";
import type { RecipeDraft } from "./api";
import { toStructuredStep } from "@/lib/stepFormat";

function groupBySection(items: RecipeDraft["ingredients"]) {
  const map = new Map<string, RecipeDraft["ingredients"]>();
  for (const it of items) {
    const key = (it.section || "Ingredients").trim();
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(it);
  }
  return Array.from(map.entries());
}

function fmtQty(q: any) {
  if (q === null || q === undefined || q === "") return "";
  return String(q);
}

export function RecipeDraftPreview({
  draft,
  activeTab,
  onTabChange,
}: {
  draft: RecipeDraft;
  activeTab: "recipe" | "storage" | "reheat" | "macros";
  onTabChange: (t: "recipe" | "storage" | "reheat" | "macros") => void;
}) {
  const tabs: Array<{ id: typeof activeTab; label: string }> = [
    { id: "recipe", label: "Recipe" },
    { id: "storage", label: "Storage" },
    { id: "reheat", label: "Reheat/Freeze" },
    { id: "macros", label: "Macros" },
  ];

  return (
    <div className="h-full rounded-2xl border bg-white/60 p-4 backdrop-blur">
      <div className="mb-3">
        <div className="text-lg font-semibold">{draft.title || "Untitled draft"}</div>
        <div className="text-sm text-neutral-600">
          {draft.yield?.servings
            ? `Serves ${draft.yield.servings}`
            : draft.yield?.servings_min || draft.yield?.servings_max
              ? `Serves ${draft.yield.servings_min ?? ""}${draft.yield?.servings_max ? `–${draft.yield.servings_max}` : ""}`
              : null}
          {draft.tags?.length ? ` • ${draft.tags.join(" · ")}` : null}
        </div>
      </div>

      <div className="mb-4 flex gap-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => onTabChange(t.id)}
            className={[
              "rounded-full px-3 py-1 text-sm transition-colors",
              activeTab === t.id ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-900 hover:bg-stone-200",
            ].join(" ")}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="max-h-[calc(100vh-220px)] overflow-auto pr-1 custom-scrollbar">
        {activeTab === "recipe" && (
          <div className="space-y-4">
            <section>
              <div className="mb-2 text-sm font-semibold text-stone-800">Ingredients</div>
              <div className="space-y-3">
                {groupBySection(draft.ingredients || []).map(([section, items]) => (
                  <div key={section} className="rounded-xl bg-white p-3 border border-stone-100">
                    <div className="mb-2 text-xs font-bold uppercase tracking-wider text-amber-600">{section}</div>
                    <ul className="space-y-1 text-sm text-stone-800">
                      {items.map((it, idx) => (
                        <li key={idx} className="flex gap-2">
                          <span className="min-w-[80px] text-stone-500 text-right font-medium">
                            {`${fmtQty(it.quantity)}${it.unit ? ` ${it.unit}` : ""}`.trim()}
                          </span>
                          <span className="flex-1">
                            {it.item}
                            {it.notes ? <span className="text-stone-400 italic"> — {it.notes}</span> : null}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <div className="mb-2 text-sm font-semibold text-stone-800">Steps</div>
              <div className="space-y-3">
                {(draft.steps || []).map((s: any, i) => {
                  let title = "";
                  let bullets: string[] = [];
                  
                  if (typeof s === "string") {
                     const parsed = toStructuredStep(s);
                     title = parsed.title;
                     bullets = parsed.bullets;
                  } else {
                     title = s.title;
                     bullets = s.bullets || [];
                  }

                  return (
                    <div key={i} className="rounded-xl border border-amber-100/50 bg-white p-4 shadow-sm">
                      <div className="flex items-start gap-3">
                        <div className="grid h-6 w-6 flex-none place-items-center rounded-lg bg-amber-50 border border-amber-100 text-amber-900 mt-0.5">
                          <span className="text-[10px] font-black">{i + 1}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-stone-900 leading-snug">{title}</div>
                          {bullets.length > 0 && (
                            <ul className="mt-2 space-y-1 text-sm text-stone-600">
                              {bullets.map((b, idx) => (
                                <li key={idx} className="flex gap-2">
                                  <span className="mt-[7px] h-1.5 w-1.5 flex-none rounded-full bg-stone-300" />
                                  <span className="min-w-0 flex-1 whitespace-normal break-words leading-snug">{b}</span>
                                  </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        )}

        {activeTab === "storage" && (
          <div className="space-y-3">
            {(draft.storage || []).length ? (
              draft.storage!.map((s, i) => (
                <div key={i} className="rounded-xl bg-white p-3 border border-stone-100">
                  <div className="text-sm font-semibold text-amber-700">{s.type || "Storage"}</div>
                  <div className="text-sm text-stone-500 mb-2">{s.duration || ""}</div>
                  <div className="text-sm text-stone-800 whitespace-pre-wrap">{s.instructions}</div>
                </div>
              ))
            ) : (
              <div className="rounded-xl bg-white p-3 text-sm text-stone-600 border border-stone-100">No storage tips provided.</div>
            )}
          </div>
        )}

        {activeTab === "reheat" && (
          <div className="space-y-3">
            {(draft.reheat || []).length ? (
              draft.reheat!.map((r, i) => (
                <div key={i} className="rounded-xl bg-white p-3 border border-stone-100">
                  <div className="text-sm font-semibold text-amber-700">{r.method || "Reheat"}</div>
                  <div className="mt-2 text-sm text-stone-800 whitespace-pre-wrap">{r.instructions || r.notes || ""}</div>
                </div>
              ))
            ) : (
              <div className="rounded-xl bg-white p-3 text-sm text-stone-600 border border-stone-100">
                No reheat/freezing tips provided.
              </div>
            )}
          </div>
        )}

        {activeTab === "macros" && (
          <div className="rounded-xl bg-white p-3 border border-stone-100">
            <div className="text-sm font-semibold mb-2">Nutrition estimate</div>
            <pre className="text-xs whitespace-pre-wrap text-stone-800 font-mono bg-stone-50 p-2 rounded">
              {JSON.stringify(draft.nutrition_estimate ?? {}, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
