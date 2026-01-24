"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Archive,
  BookOpen,
  Calendar,
  Camera,
  CheckCircle2,
  ChefHat,
  ChevronRight,
  Flame,
  Layers,
  Plus,
  RotateCcw,
  Search,
  Sparkles,
  Users,
  X,
  Zap,
} from "lucide-react";

// shadcn/ui
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

/**
 * TasteOS — Gemini-inspired UI + shadcn primitives
 * Update: more AMBER + method sheet shows single-row tradeoff explanations.
 * Cook Mode: Step cards (first variant).
 */

type ViewKey = "today" | "plan" | "pantry" | "recipes" | "family";

type Vibe = "tired" | "normal" | "motivated";

type MealType = "lunch" | "dinner";

type Method = {
  name: string;
  impact: string;
  flavor: string;
  time: string;
  cleanup: string;
  effort: "Low" | "Med" | "High";
  icon: React.ReactNode;
};

type Meal = {
  title: string;
  image: string;
  pantryMatch: number;
  goalFit: "Low" | "OK" | "Great";
  isAnchor: boolean;
  currentMethodIdx: number;
  methods: Method[];
};

type PantryItem = {
  name: string;
  expiry: string;
  qty?: string;
  tint: string;
};

type CookStep = {
  title: string;
  minutes: number;
  bullets: string[];
  tip?: string;
};

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function hashString(input: string) {
  // deterministic tiny hash for stable placeholder palette
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

function svgPhotoDataUrl(seed: string, label: string) {
  const palettes = [
    { a: "#fef3c7", b: "#fff7ed", c: "#fde68a" },
    { a: "#ffedd5", b: "#fff7ed", c: "#fef3c7" },
    { a: "#fef3c7", b: "#ffedd5", c: "#fde68a" },
    { a: "#fff7ed", b: "#fef3c7", c: "#ffedd5" },
    { a: "#f5f5f4", b: "#fff7ed", c: "#fef3c7" },
  ];
  const i = hashString(seed) % palettes.length;
  const p = palettes[i];
  const short = (label || "").trim().slice(0, 26);
  const safe = short
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const svg = `
  <svg xmlns='http://www.w3.org/2000/svg' width='1200' height='750' viewBox='0 0 1200 750'>
    <defs>
      <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
        <stop offset='0' stop-color='${p.a}'/>
        <stop offset='0.55' stop-color='${p.b}'/>
        <stop offset='1' stop-color='${p.c}'/>
      </linearGradient>
      <filter id='s' x='-20%' y='-20%' width='140%' height='140%'>
        <feDropShadow dx='0' dy='10' stdDeviation='12' flood-color='#000' flood-opacity='0.18'/>
      </filter>
    </defs>
    <rect width='1200' height='750' rx='88' fill='url(#g)'/>

    <circle cx='420' cy='360' r='210' fill='rgba(255,255,255,0.68)' filter='url(#s)'/>
    <circle cx='420' cy='360' r='148' fill='rgba(0,0,0,0.06)'/>

    <path d='M740 240c70 0 126 56 126 126s-56 126-126 126c-40 0-76-18-99-48'
          fill='none' stroke='rgba(0,0,0,0.14)' stroke-width='36' stroke-linecap='round'/>
    <path d='M760 560c64 44 126 40 186-18'
          fill='none' stroke='rgba(0,0,0,0.12)' stroke-width='34' stroke-linecap='round'/>

    <text x='74' y='108' font-family='ui-sans-serif, system-ui' font-size='34' fill='rgba(0,0,0,0.50)'>TasteOS</text>
    <text x='74' y='176' font-family='ui-serif, Georgia, serif' font-size='54' font-weight='700' fill='rgba(0,0,0,0.78)'>${safe}</text>
    <text x='74' y='224' font-family='ui-sans-serif, system-ui' font-size='22' fill='rgba(0,0,0,0.45)'>Placeholder photo</text>
  </svg>`;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function SmartImg({ src, alt, seed, className }: { src: string; alt: string; seed: string; className: string }) {
  const [fallback, setFallback] = useState(false);
  const resolvedSrc = fallback ? svgPhotoDataUrl(seed, alt) : src;
  return (
    <img
      src={resolvedSrc}
      alt={alt}
      className={className}
      loading="lazy"
      onError={() => setFallback(true)}
    />
  );
}

function NavItem({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex flex-1 flex-col items-center gap-1 py-2 transition-colors",
        active ? "text-amber-950" : "text-stone-300 hover:text-amber-800"
      )}
      type="button"
      aria-label={label}
    >
      <div className={cn("rounded-2xl p-1", active && "bg-amber-100/70")}>{icon}</div>
      <span className="text-[10px] font-black uppercase tracking-tighter">{label}</span>
    </button>
  );
}

function VibePill({ vibe, setVibe }: { vibe: Vibe; setVibe: (v: Vibe) => void }) {
  const options: Vibe[] = ["tired", "normal", "motivated"];
  return (
    <div className="rounded-2xl border border-amber-100/70 bg-amber-100/30 p-1.5">
      <div className="flex">
        {options.map((v) => (
          <button
            key={v}
            onClick={() => setVibe(v)}
            type="button"
            className={cn(
              "flex-1 rounded-xl px-2 py-3 text-[10px] font-black uppercase tracking-widest transition-all duration-300",
              vibe === v ? "bg-white text-stone-900 shadow-sm" : "text-stone-500 hover:text-amber-800"
            )}
          >
            {v}
          </button>
        ))}
      </div>
    </div>
  );
}

function MethodChip({ m }: { m: Method }) {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-stone-50 bg-white px-3 py-1 text-[10px] font-bold uppercase text-stone-500 shadow-sm">
      {m.icon}
      <span>{m.name}</span>
    </div>
  );
}

function tradeoffLine(m: Method) {
  return `${m.impact} • ${m.time} • Cleanup: ${m.cleanup} • Effort: ${m.effort}`;
}

function cookStepsForMeal(mealTitle: string, methodName: string): CookStep[] {
  const title = mealTitle.toLowerCase();
  const method = methodName.toLowerCase();

  // Special-ish flows for your recent patterns
  if (title.includes("enchilad")) {
    const bakeMinutes = method.includes("air") ? 18 : 25;
    const preheat = method.includes("air") ? "Preheat air fryer" : "Preheat oven";
    return [
      {
        title: "Set up + prep",
        minutes: 8,
        bullets: [
          "Pull tortillas, cheese, and sauce to the counter",
          "Warm tortillas briefly so they don't crack",
          "Shred chicken and taste sauce (salt/lime if needed)",
        ],
        tip: "If you're tired: use store sauce + pre-shredded cheese. No shame, same W.",
      },
      {
        title: "Build the tray",
        minutes: 12,
        bullets: [
          "Spread a thin layer of sauce in the baking dish",
          "Fill tortillas, roll tight, and place seam-side down",
          "Top with sauce + cheese (don't drown if sauce is thin)",
        ],
        tip: "If sauce is thin: reduce it 3–5 min in a pan or add a little cheese to thicken.",
      },
      {
        title: `${preheat} + cook`,
        minutes: bakeMinutes,
        bullets: [
          "Cook until cheese bubbles and edges look set",
          "If using air fryer: work in batches or use a small pan",
          "Rest 5 minutes before slicing",
        ],
        tip: "Crispier top: broil 1–2 min at the end (watch closely).",
      },
      {
        title: "Serve + store",
        minutes: 6,
        bullets: [
          "Add toppings (yogurt/sour cream, cilantro, hot sauce)",
          "Cool leftovers before sealing",
          "Fridge 3–4 days; freeze up to 2–3 months",
        ],
        tip: "Reheat: oven/air fryer for texture; microwave for speed.",
      },
    ];
  }

  if (title.includes("leftover") || title.includes("casserole")) {
    return [
      {
        title: "Choose reheat method",
        minutes: 2,
        bullets: [
          "Microwave = fastest",
          "Oven/air fryer = better texture",
          "Add a splash of water/stock if it's dry",
        ],
        tip: "Texture matters? Use oven/air fryer. Tired? Microwave + finish 2 min in air fryer.",
      },
      {
        title: "Reheat",
        minutes: method.includes("micro") ? 4 : 15,
        bullets: [
          "Heat until steaming hot through the center",
          "Stir/flip once halfway",
          "Taste + add salt/pepper if needed",
        ],
      },
      {
        title: "Plate + reset",
        minutes: 5,
        bullets: [
          "Add something fresh (lime, herbs, salsa, salad)",
          "Portion remaining leftovers",
          "Quick cleanup so tomorrow-you is happy",
        ],
      },
    ];
  }

  // Generic default
  return [
    {
      title: "Prep",
      minutes: 10,
      bullets: ["Gather ingredients", "Set up tools", "Do quick chop/measure"],
    },
    {
      title: "Cook",
      minutes: 25,
      bullets: ["Follow main steps", "Taste and adjust seasoning", "Watch texture/heat"],
    },
    {
      title: "Finish + store",
      minutes: 8,
      bullets: ["Plate", "Pack leftovers", "Note storage time + next reheat"],
    },
  ];
}

function MealHeroCard({
  type,
  meal,
  onOpenMethods,
}: {
  type: MealType;
  meal: Meal;
  onOpenMethods: () => void;
}) {
  const method = meal.methods[meal.currentMethodIdx];

  return (
    <div className="group cursor-pointer" onClick={onOpenMethods} role="button" tabIndex={0}>
      <div className="mb-3 flex items-end justify-between">
        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-stone-300">{type}</h3>
        <MethodChip m={method} />
      </div>

      <div className="relative aspect-[16/10] overflow-hidden rounded-[2.5rem] border border-stone-100 shadow-lg">
        <SmartImg
          src={meal.image}
          alt={meal.title}
          seed={meal.title}
          className="h-full w-full object-cover transition-transform duration-1000 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />

        {meal.isAnchor ? (
          <div className="absolute left-5 top-5 flex items-center gap-1.5 rounded-xl border border-amber-100 bg-amber-50/90 px-3 py-1.5 text-[9px] font-black uppercase tracking-widest text-amber-900 shadow-sm backdrop-blur-md">
            <Layers size={10} strokeWidth={3} />
            Anchor
          </div>
        ) : null}

        <div className="absolute bottom-6 left-6 right-6">
          <h2 className="mb-3 font-serif text-2xl leading-tight tracking-tight text-white">{meal.title}</h2>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
              Match {meal.pantryMatch}%
            </span>
            <span className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
              Fit: {meal.goalFit}
            </span>
            <span className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
              {method.time}
            </span>
            <span className="inline-flex items-center gap-1 rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
              <ChevronRight size={12} />
              Methods
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MethodsSheet({
  open,
  onClose,
  mealTitle,
  methods,
  currentIdx,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  mealTitle: string;
  methods: Method[];
  currentIdx: number;
  onSelect: (idx: number) => void;
}) {
  const current = methods[currentIdx];

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[100] flex items-end bg-black/40 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="w-full rounded-t-[3rem] bg-white p-8 pb-10 shadow-2xl"
            initial={{ y: 60, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 60, opacity: 0 }}
            transition={{ duration: 0.22 }}
          >
            <div className="mb-6 flex items-start justify-between">
              <div className="min-w-0">
                <h3 className="truncate font-serif text-2xl text-stone-900">{mealTitle}</h3>
                <p className="mt-1 text-[10px] font-black uppercase tracking-widest text-amber-700/70">Select cooking method</p>

                {current ? (
                  <div className="mt-3 inline-flex max-w-full items-center gap-2 rounded-2xl border border-amber-100 bg-amber-50/70 px-4 py-2 text-[11px] font-semibold text-stone-800">
                    <span className="inline-flex items-center gap-2 text-amber-800">
                      {current.icon}
                      <span className="text-[10px] font-black uppercase tracking-widest">Tradeoffs</span>
                    </span>
                    <span className="text-stone-400">•</span>
                    <span className="truncate text-stone-800">{tradeoffLine(current)}</span>
                  </div>
                ) : null}
              </div>

              <button
                onClick={onClose}
                type="button"
                className="rounded-full bg-stone-100 p-2 text-stone-400"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-3">
              {methods.map((m, i) => {
                const selected = i === currentIdx;
                return (
                  <button
                    key={m.name}
                    onClick={() => onSelect(i)}
                    type="button"
                    className={cn(
                      "w-full rounded-[2rem] border-2 p-5 text-left transition-all",
                      selected ? "border-amber-500 bg-amber-50/40" : "border-stone-100 bg-stone-50/50 hover:bg-amber-50/20"
                    )}
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={cn("rounded-xl bg-white p-2 shadow-sm", selected && "ring-1 ring-amber-200")}>{m.icon}</div>
                        <span className="font-bold text-stone-900">{m.name}</span>
                      </div>
                      {selected ? <CheckCircle2 size={20} className="text-amber-600" /> : null}
                    </div>

                    <div className="grid grid-cols-3 gap-2">
                      <div className="flex flex-col">
                        <span className="text-[8px] font-black uppercase text-stone-400">Texture</span>
                        <span className="text-xs font-bold text-stone-900">{m.impact}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[8px] font-black uppercase text-stone-400">Time</span>
                        <span className="text-xs font-bold text-stone-900">{m.time}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[8px] font-black uppercase text-stone-400">Effort</span>
                        <span className="text-xs font-bold text-stone-900">{m.effort}</span>
                      </div>
                    </div>

                    <div className="mt-3 rounded-2xl border border-stone-100 bg-white/70 px-4 py-2 text-[11px] font-semibold text-stone-700">
                      {tradeoffLine(m)}
                    </div>
                  </button>
                );
              })}
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

function ScanResultModal({
  open,
  onConfirm,
  onClose,
  items,
}: {
  open: boolean;
  onConfirm: () => void;
  onClose: () => void;
  items: Array<{ name: string; qty: string; expiry: string }>;
}) {
  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[110] flex items-center justify-center bg-stone-900/60 p-6 backdrop-blur-md"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="w-full rounded-[2.5rem] bg-white p-8 shadow-2xl"
            initial={{ scale: 0.97, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.97, opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-2xl bg-amber-100 p-3 text-amber-700">
                <Sparkles />
              </div>
              <div className="flex-1">
                <h3 className="font-serif text-xl text-stone-900">Items Detected</h3>
                <p className="mt-1 text-[10px] font-black uppercase tracking-widest text-stone-400">Confirm to add to pantry</p>
              </div>
              <button
                onClick={onClose}
                type="button"
                className="rounded-full bg-stone-100 p-2 text-stone-400"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mb-8 space-y-3">
              {items.map((item) => (
                <div
                  key={item.name}
                  className="flex items-center justify-between rounded-2xl border border-stone-100 bg-stone-50 p-4"
                >
                  <span className="text-sm font-bold text-stone-800">{item.name}</span>
                  <div className="text-right">
                    <p className="text-[10px] font-black uppercase tracking-tighter text-stone-400">Qty: {item.qty}</p>
                    <p className="text-[10px] font-black uppercase tracking-tighter text-amber-700">Exp: {item.expiry}</p>
                  </div>
                </div>
              ))}
            </div>

            <Button
              onClick={onConfirm}
              className="h-12 w-full rounded-2xl bg-stone-900 text-xs font-black uppercase tracking-widest text-white hover:bg-stone-900"
            >
              Add to Pantry
            </Button>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

function StepCard({
  step,
  index,
  active,
  checks,
  onToggle,
  showIndex = true,
  showBadge = true,
}: {
  step: CookStep;
  index: number;
  active: boolean;
  checks: Record<string, boolean>;
  onToggle: (key: string) => void;
  showIndex?: boolean;
  showBadge?: boolean;
}) {
  return (
    <Card
      className={cn(
        "rounded-[2.5rem] border-amber-100/50 shadow-sm",
        active ? "bg-white" : "bg-white/70"
      )}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {showIndex ? (
              <div
                className={cn(
                  "grid h-10 w-10 place-items-center rounded-2xl border border-amber-100 bg-amber-50 text-amber-900",
                  active && "ring-1 ring-amber-200"
                )}
              >
                <span className="text-sm font-black">{index + 1}</span>
              </div>
            ) : null}
            <div className="min-w-0">
              <CardTitle className="truncate font-serif text-xl text-stone-900">{step.title}</CardTitle>
              <p className="mt-1 text-[10px] font-black uppercase tracking-widest text-stone-400">~{step.minutes} min</p>
            </div>
          </div>
          {showBadge ? (
            <Badge className="rounded-full bg-amber-100/70 text-amber-950 hover:bg-amber-100/70" variant="secondary">
              Step
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          {step.bullets.map((b, i) => {
            const key = `${index}:${i}`;
            const checked = Boolean(checks[key]);
            return (
              <button
                key={key}
                type="button"
                onClick={() => onToggle(key)}
                className={cn(
                  "flex w-full items-start gap-3 rounded-2xl border border-stone-100 bg-stone-50/70 p-3 text-left",
                  checked && "border-amber-200 bg-amber-50/50"
                )}
              >
                <div
                  className={cn(
                    "mt-0.5 grid h-6 w-6 flex-none place-items-center rounded-xl border border-stone-200 bg-white",
                    checked && "border-amber-300 bg-amber-100/70"
                  )}
                >
                  {checked ? <CheckCircle2 className="h-4 w-4 text-amber-700" /> : null}
                </div>
                <div className={cn("text-sm font-semibold", checked ? "text-stone-700" : "text-stone-800")}>
                  {b}
                </div>
              </button>
            );
          })}
        </div>

        {step.tip ? (
          <div className="rounded-2xl border border-amber-100 bg-amber-50/60 p-4">
            <div className="text-[10px] font-black uppercase tracking-widest text-amber-800">Chef tip</div>
            <div className="mt-1 text-sm font-semibold text-stone-800">{step.tip}</div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CookTimelineItem({
  step,
  index,
  isActive,
  isDone,
  isLast,
  onSelect,
  checks,
  onToggle,
}: {
  step: CookStep;
  index: number;
  isActive: boolean;
  isDone: boolean;
  isLast: boolean;
  onSelect: () => void;
  checks: Record<string, boolean>;
  onToggle: (key: string) => void;
}) {
  return (
    <div className="grid grid-cols-[28px_1fr] gap-4">
      <div className="relative flex justify-center">
        {!isLast ? <div className="absolute top-9 bottom-0 w-px bg-amber-300/70" /> : null}
        <button
          type="button"
          onClick={onSelect}
          className={cn(
            "mt-1 grid h-7 w-7 place-items-center rounded-2xl border text-[11px] font-black",
            isDone
              ? "border-amber-400 bg-amber-500 text-white"
              : isActive
                ? "border-amber-300 bg-amber-100 text-amber-950"
                : "border-stone-200 bg-white text-stone-600 hover:border-amber-200"
          )}
          aria-label={`Go to step ${index + 1}`}
        >
          {isDone ? <CheckCircle2 className="h-4 w-4" /> : <span>{index + 1}</span>}
        </button>
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={onSelect}
        onKeyDown={(e) => e.key === 'Enter' && onSelect()}
        className="text-left cursor-pointer"
      >
        <StepCard
          step={step}
          index={index}
          active={isActive}
          checks={checks}
          onToggle={onToggle}
          showIndex={false}
          showBadge={false}
        />
      </div>
    </div>
  );
}

function CookModeOverlay({
  open,
  onClose,
  meal,
  method,
  steps,
  stepIdx,
  setStepIdx,
  checks,
  onToggle,
}: {
  open: boolean;
  onClose: () => void;
  meal: Meal;
  method: Method;
  steps: CookStep[];
  stepIdx: number;
  setStepIdx: (n: number) => void;
  checks: Record<string, boolean>;
  onToggle: (key: string) => void;
}) {
  const progress = steps.length > 1 ? Math.round(((stepIdx + 1) / steps.length) * 100) : 0;

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[120] flex flex-col bg-[#FAF9F6]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* amber wash */}
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-amber-50/70 via-transparent to-transparent" />

          {/* header */}
          <div className="relative px-6 pt-6">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={onClose}
                className="rounded-2xl border border-amber-100 bg-white/80 p-3 text-stone-700 shadow-sm"
                aria-label="Exit cook mode"
              >
                <X className="h-5 w-5" />
              </button>
              <div className="flex items-center gap-2">
                <Badge className="rounded-full bg-amber-100/70 text-amber-950 hover:bg-amber-100/70" variant="secondary">
                  Cook Mode
                </Badge>
                <Badge className="rounded-full bg-white text-stone-600 hover:bg-white" variant="secondary">
                  {method.name}
                </Badge>
              </div>
            </div>

            <div className="mt-4 overflow-hidden rounded-[2.5rem] border border-amber-100/50 bg-white shadow-sm">
              <div className="relative h-[220px] w-full sm:h-[260px]">
                <SmartImg
                  src={meal.image}
                  alt={meal.title}
                  seed={meal.title}
                  className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent" />
                <div className="absolute bottom-4 left-4 right-4">
                  <div className="font-serif text-2xl leading-tight text-white">{meal.title}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
                      {tradeoffLine(method)}
                    </span>
                    <span className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
                      Progress {progress}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* steps */}
          <div className="relative flex-1 overflow-y-auto px-6 pb-28 pt-6 no-scrollbar">
            <div className="sticky top-0 z-10 -mx-6 mb-4 bg-gradient-to-b from-[#FAF9F6] via-[#FAF9F6]/90 to-transparent px-6 pb-3 pt-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-stone-600">
                  <span className="inline-flex h-2 w-2 rounded-full bg-amber-500" />
                  Step timeline
                </div>
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-stone-500">
                  Tap a node
                  <ChevronRight className="h-4 w-4 rotate-90 text-amber-700" />
                </div>
              </div>
            </div>

            <div className="space-y-5">
              {steps.map((s, i) => {
                const done = s.bullets.every((_, bi) => Boolean(checks[`${i}:${bi}`]));
                return (
                  <CookTimelineItem
                    key={`${s.title}-${i}`}
                    step={s}
                    index={i}
                    isActive={i === stepIdx}
                    isDone={done}
                    isLast={i === steps.length - 1}
                    onSelect={() => setStepIdx(i)}
                    checks={checks}
                    onToggle={onToggle}
                  />
                );
              })}
            </div>

            <div className="mt-6">
              <Card className="rounded-[2.5rem] border-amber-100/50 bg-white shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-stone-900">Ask while you cook</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm font-semibold text-stone-500">
                    e.g. "Sauce is thin — how do I thicken without ruining it?"
                  </div>
                  <div className="mt-3 flex gap-2">
                    <Button variant="outline" className="h-11 flex-1 rounded-2xl border-amber-100/60 hover:bg-amber-50/60">
                      Swap ingredient
                    </Button>
                    <Button variant="outline" className="h-11 flex-1 rounded-2xl border-amber-100/60 hover:bg-amber-50/60">
                      Scale recipe
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* bottom controls */}
          <div className="fixed bottom-0 left-0 right-0 z-[130] border-t border-amber-100/60 bg-white/90 px-6 pb-6 pt-4 backdrop-blur-2xl">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-[10px] font-black uppercase tracking-widest text-stone-500">
                Step {Math.min(stepIdx + 1, steps.length)} of {steps.length}
              </div>
              <div className="text-[10px] font-black uppercase tracking-widest text-amber-800">{steps[stepIdx]?.minutes ?? 0} min</div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="h-12 flex-1 rounded-2xl border-amber-100/60 hover:bg-amber-50/60"
                onClick={() => setStepIdx(Math.max(0, stepIdx - 1))}
                disabled={stepIdx === 0}
              >
                Previous
              </Button>
              <Button
                className="h-12 flex-1 rounded-2xl bg-stone-900 text-xs font-black uppercase tracking-widest text-white hover:bg-stone-900"
                onClick={() => setStepIdx(Math.min(steps.length - 1, stepIdx + 1))}
                disabled={stepIdx >= steps.length - 1}
              >
                Next
              </Button>
            </div>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

export default function TasteOSPrototypeGeminiStyle() {
  const [currentView, setCurrentView] = useState<ViewKey>("today");
  const [vibe, setVibe] = useState<Vibe>("normal");

  // method sheet
  const [selectedMealType, setSelectedMealType] = useState<MealType | null>(null);

  // pantry scan
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<Array<{ name: string; qty: string; expiry: string }> | null>(null);

  // cook mode
  const [cookOpen, setCookOpen] = useState(false);
  const [cookMealType, setCookMealType] = useState<MealType>("dinner");
  const [cookStepIdx, setCookStepIdx] = useState(0);
  const [cookChecks, setCookChecks] = useState<Record<string, boolean>>({});

  // avoid setState after unmount when simulating scan
  const scanTimerRef = useRef<number | null>(null);
  useEffect(() => {
    return () => {
      if (scanTimerRef.current) window.clearTimeout(scanTimerRef.current);
    };
  }, []);

  const [dateLabel, setDateLabel] = useState("");

  useEffect(() => {
    const d = new Date();
    const weekday = d.toLocaleDateString(undefined, { weekday: "long" });
    const monthDay = d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    setDateLabel(`${weekday}, ${monthDay}`);
  }, []);

  // --- MOCK DATA ---
  const [dailyMeals, setDailyMeals] = useState<Record<MealType, Meal>>({
    lunch: {
      title: "Beef Casserole Leftovers",
      image: "https://images.unsplash.com/photo-1541529086526-db283c563270?auto=format&fit=crop&q=80&w=1400",
      pantryMatch: 100,
      goalFit: "Great",
      isAnchor: false,
      currentMethodIdx: 0,
      methods: [
        {
          name: "Microwave",
          impact: "Fastest",
          flavor: "Soft",
          time: "3m",
          cleanup: "None",
          effort: "Low",
          icon: <Zap size={14} />,
        },
        {
          name: "Oven",
          impact: "Better crust",
          flavor: "Deep",
          time: "15m",
          cleanup: "Low",
          effort: "Med",
          icon: <Flame size={14} />,
        },
      ],
    },
    dinner: {
      title: "Salsa Verde Enchiladas",
      image: "https://images.unsplash.com/photo-1534353875273-b5887cc1abf5?auto=format&fit=crop&q=80&w=1400",
      pantryMatch: 85,
      goalFit: "OK",
      isAnchor: true,
      currentMethodIdx: 1,
      methods: [
        {
          name: "Instant Pot",
          impact: "Tender/shredded",
          flavor: "Mellow",
          time: "40m",
          cleanup: "1 pot",
          effort: "Low",
          icon: <Zap size={14} />,
        },
        {
          name: "Dutch Oven",
          impact: "Caramelized",
          flavor: "Richest",
          time: "75m",
          cleanup: "Med",
          effort: "Med",
          icon: <Flame size={14} />,
        },
        {
          name: "Air Fryer",
          impact: "Crispy edges",
          flavor: "Zesty",
          time: "25m",
          cleanup: "Low",
          effort: "Low",
          icon: <Zap size={14} />,
        },
      ],
    },
  });

  const [pantryItems, setPantryItems] = useState<PantryItem[]>([
    { name: "Greek Yogurt", expiry: "2 days", qty: "1 cup", tint: "bg-amber-50/70" },
    { name: "Cilantro", expiry: "Today", qty: "1 bunch", tint: "bg-amber-100/50" },
    { name: "Half Onion", expiry: "3 days", qty: "1/2", tint: "bg-orange-50" },
  ]);

  // --- Derived ---
  const activeMeal = selectedMealType ? dailyMeals[selectedMealType] : null;

  const cookMeal = dailyMeals[cookMealType];
  const cookMethod = cookMeal.methods[cookMeal.currentMethodIdx];

  const cookSteps = useMemo(() => {
    return cookStepsForMeal(cookMeal.title, cookMethod.name);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cookMeal.title, cookMethod.name]);

  useEffect(() => {
    if (!cookOpen) return;
    setCookStepIdx(0);
    setCookChecks({});
  }, [cookOpen]);

  const toggleCookCheck = (key: string) => {
    setCookChecks((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // --- HANDLERS ---
  const handleScan = () => {
    if (isScanning) return;
    setIsScanning(true);
    scanTimerRef.current = window.setTimeout(() => {
      setScanResult([
        { name: "Avocados", qty: "3 ct", expiry: "5 days" },
        { name: "Corn Tortillas", qty: "1 pack", expiry: "12 days" },
      ]);
      setIsScanning(false);
    }, 1400);
  };

  const confirmScan = () => {
    if (!scanResult) return;
    const newItems: PantryItem[] = scanResult.map((item) => ({
      name: item.name,
      qty: item.qty,
      expiry: item.expiry,
      tint: "bg-amber-50/40",
    }));
    setPantryItems((prev) => [...prev, ...newItems]);
    setScanResult(null);
  };

  const closeScanModal = () => setScanResult(null);

  const startCookMode = () => {
    // For now default to dinner (anchor) — later we can add a picker.
    setCookMealType("dinner");
    setCookOpen(true);
  };

  return (
    <div className="relative mx-auto flex h-screen max-w-md flex-col overflow-hidden bg-[#FAF9F6] font-sans text-stone-800 shadow-2xl">
      {/* subtle amber wash */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-amber-50/60 via-transparent to-transparent" />

      {/* COOK MODE OVERLAY */}
      <CookModeOverlay
        open={cookOpen}
        onClose={() => setCookOpen(false)}
        meal={cookMeal}
        method={cookMethod}
        steps={cookSteps}
        stepIdx={cookStepIdx}
        setStepIdx={setCookStepIdx}
        checks={cookChecks}
        onToggle={toggleCookCheck}
      />

      {/* METHOD SWITCHER SHEET */}
      <MethodsSheet
        open={Boolean(selectedMealType && activeMeal)}
        onClose={() => setSelectedMealType(null)}
        mealTitle={activeMeal?.title ?? ""}
        methods={activeMeal?.methods ?? []}
        currentIdx={activeMeal?.currentMethodIdx ?? 0}
        onSelect={(idx) => {
          if (!selectedMealType) return;
          setDailyMeals((prev) => ({
            ...prev,
            [selectedMealType]: { ...prev[selectedMealType], currentMethodIdx: idx },
          }));
          setSelectedMealType(null);
        }}
      />

      {/* SCAN RESULT MODAL */}
      <ScanResultModal open={Boolean(scanResult)} items={scanResult ?? []} onConfirm={confirmScan} onClose={closeScanModal} />

      {/* MAIN CONTENT */}
      <div className="relative no-scrollbar flex-1 overflow-y-auto pb-32">
        {currentView === "today" ? (
          <motion.div
            className="px-6 pt-12"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <header className="mb-8">
              <h1 className="font-serif text-3xl leading-tight text-stone-900">Good morning.</h1>
              <p className="mt-1 text-[10px] font-black uppercase tracking-[0.2em] text-stone-400">{dateLabel}</p>
            </header>

            <div className="mb-10">
              <VibePill vibe={vibe} setVibe={setVibe} />
              <div className="mt-3 flex items-center justify-between">
                <Badge className="rounded-full bg-white text-stone-600 hover:bg-white" variant="secondary">
                  Lunch + Dinner
                </Badge>
                <Badge className="rounded-full bg-amber-100/70 text-amber-950 hover:bg-amber-100/70" variant="secondary">
                  Leftovers: Medium
                </Badge>
              </div>
            </div>

            <div className="space-y-8">
              <MealHeroCard type="lunch" meal={dailyMeals.lunch} onOpenMethods={() => setSelectedMealType("lunch")} />
              <MealHeroCard type="dinner" meal={dailyMeals.dinner} onOpenMethods={() => setSelectedMealType("dinner")} />
            </div>

            {/* Fridge pressure / Use soon */}
            <div className="mt-12">
              <h3 className="mb-4 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-stone-900">
                <Archive size={14} className="text-amber-600" /> Fridge Pressure
              </h3>
              <div className="no-scrollbar flex gap-4 overflow-x-auto pb-6">
                {pantryItems.map((item) => (
                  <div
                    key={item.name}
                    className={cn(
                      item.tint,
                      "min-w-[140px] rounded-[2rem] border border-amber-100/40 p-5"
                    )}
                  >
                    <span className="text-sm font-bold tracking-tight text-stone-800">{item.name}</span>
                    <span className="mt-6 block text-[9px] font-black uppercase tracking-widest text-stone-500">
                      {item.expiry} left
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick actions */}
            <div className="mt-4">
              <Card className="rounded-[2.5rem] border-amber-100/50 bg-white shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-stone-900">Quick actions</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-2">
                  <Button variant="outline" className="h-12 rounded-2xl border-amber-100/60 justify-start hover:bg-amber-50/60">
                    <Calendar className="mr-2 h-4 w-4" /> Auto-plan
                  </Button>
                  <Button variant="outline" className="h-12 rounded-2xl border-amber-100/60 justify-start hover:bg-amber-50/60">
                    <Archive className="mr-2 h-4 w-4" /> Pantry
                  </Button>
                  <Button variant="outline" className="h-12 rounded-2xl border-amber-100/60 justify-start hover:bg-amber-50/60">
                    <BookOpen className="mr-2 h-4 w-4" /> Import
                  </Button>
                  <Button variant="outline" className="h-12 rounded-2xl border-amber-100/60 justify-start hover:bg-amber-50/60">
                    <Plus className="mr-2 h-4 w-4" /> Add
                  </Button>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        ) : null}

        {currentView === "pantry" ? (
          <motion.div
            className="px-6 pt-12"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.28 }}
          >
            <header className="mb-8 flex items-end justify-between">
              <div>
                <h1 className="font-serif text-3xl leading-tight text-stone-900">My Pantry.</h1>
                <p className="mt-1 text-[10px] font-black uppercase tracking-widest text-stone-400">Smart Tracking Active</p>
              </div>

              <button
                onClick={handleScan}
                type="button"
                className={cn(
                  "rounded-3xl bg-stone-900 p-4 text-white shadow-xl transition-all active:scale-95",
                  isScanning && "animate-pulse"
                )}
                aria-label="Scan"
              >
                {isScanning ? <RotateCcw size={20} className="animate-spin" /> : <Camera size={20} />}
              </button>
            </header>

            <div className="relative mb-10">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-stone-300" size={18} />
              <input
                type="text"
                placeholder="Search my kitchen..."
                className="w-full rounded-2xl border border-transparent bg-amber-50/40 py-4 pl-12 pr-4 text-sm font-medium shadow-sm outline-none transition-all focus:border-amber-200 focus:bg-white"
              />
            </div>

            <section className="mb-10">
              <h3 className="mb-5 text-[10px] font-black uppercase tracking-[0.2em] text-stone-400">Current Inventory</h3>

              <Card className="overflow-hidden rounded-[2.5rem] border-amber-100/50 bg-white shadow-sm">
                <CardContent className="p-0">
                  {pantryItems.map((item) => (
                    <div
                      key={item.name}
                      className="flex items-center justify-between border-b border-stone-50 p-5 last:border-0 hover:bg-amber-50/30"
                    >
                      <div>
                        <p className="text-sm font-bold text-stone-800">{item.name}</p>
                        <p className="text-[9px] font-black uppercase tracking-widest text-stone-400">{item.qty ?? ""}</p>
                      </div>
                      <span className="rounded-lg bg-amber-100/70 px-2 py-1 text-[9px] font-black uppercase tracking-widest text-amber-950">
                        Exp: {item.expiry}
                      </span>
                    </div>
                  ))}

                  <button
                    type="button"
                    className="flex w-full items-center justify-center gap-2 py-4 text-stone-300 transition-colors hover:text-amber-800"
                  >
                    <Plus size={16} />
                    <span className="text-[10px] font-black uppercase tracking-widest">Manual Add</span>
                  </button>
                </CardContent>
              </Card>

              <div className="mt-6">
                <Separator />
                <div className="mt-4 rounded-[2.5rem] border border-amber-100/50 bg-white p-5 shadow-sm">
                  <div className="flex items-center gap-2 text-sm font-semibold text-stone-900">
                    <ChefHat className="h-4 w-4" /> Pantry intelligence
                  </div>
                  <p className="mt-1 text-sm text-stone-600">
                    TasteOS tracks "use soon" items, proposes substitutions, and auto-updates the grocery list when your plan changes.
                  </p>
                </div>
              </div>
            </section>
          </motion.div>
        ) : null}

        {currentView !== "today" && currentView !== "pantry" ? (
          <div className="px-6 pt-12">
            <Card className="rounded-[2.5rem] border-amber-100/50 bg-white shadow-sm">
              <CardHeader>
                <CardTitle className="font-serif text-2xl text-stone-900">
                  {currentView[0].toUpperCase() + currentView.slice(1)}
                </CardTitle>
                <p className="mt-1 text-sm text-stone-600">Placeholder screen — we'll design this next.</p>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-[2rem] border border-amber-100/40 bg-amber-50/40 p-3">
                    <SmartImg
                      src="https://images.unsplash.com/photo-1551218808-94e220e084d2?auto=format&fit=crop&q=80&w=1200"
                      alt="Placeholder"
                      seed="placeholder"
                      className="h-20 w-full rounded-[1.5rem] object-cover"
                    />
                    <div className="mt-2 text-sm font-semibold text-stone-900">Beautiful cards</div>
                    <div className="mt-1 text-[10px] font-black uppercase tracking-widest text-stone-500">Warm amber</div>
                  </div>
                  <div className="rounded-[2rem] border border-amber-100/40 bg-amber-50/40 p-3">
                    <SmartImg
                      src="https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&q=80&w=1200"
                      alt="Placeholder"
                      seed="placeholder2"
                      className="h-20 w-full rounded-[1.5rem] object-cover"
                    />
                    <div className="mt-2 text-sm font-semibold text-stone-900">Agent diffs</div>
                    <div className="mt-1 text-[10px] font-black uppercase tracking-widest text-stone-500">Safe approvals</div>
                  </div>
                </div>

                <Separator />

                <div className="grid grid-cols-2 gap-2">
                  <Button variant="outline" className="h-12 rounded-2xl border-amber-100/60 hover:bg-amber-50/60">
                    Open settings
                  </Button>
                  <Button className="h-12 rounded-2xl bg-stone-900 text-white hover:bg-stone-900">Add sample</Button>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>

      {/* START COOK MODE CTA */}
      {currentView === "today" && !cookOpen ? (
        <div className="pointer-events-none fixed bottom-28 left-0 right-0 z-40 px-6">
          <div className="pointer-events-none absolute -inset-x-6 -top-10 h-20 bg-gradient-to-t from-[#FAF9F6] via-[#FAF9F6]/70 to-transparent" />
          <button
            type="button"
            onClick={startCookMode}
            className="pointer-events-auto flex w-full items-center justify-center gap-3 rounded-[2rem] bg-stone-900 py-5 text-xs font-black uppercase tracking-[0.3em] text-white shadow-2xl transition-all active:scale-95 hover:bg-stone-900"
          >
            <Flame size={18} className="text-amber-400" />
            Start Cook Mode
          </button>
        </div>
      ) : null}

      {/* NAV */}
      {!cookOpen ? (
        <nav className="fixed bottom-0 left-0 right-0 z-50 flex justify-between border-t border-amber-100/60 bg-white/90 px-4 pb-8 pt-3 backdrop-blur-2xl shadow-[0_-10px_40px_rgba(0,0,0,0.03)]">
          <NavItem
            label="Today"
            icon={<ChefHat size={24} strokeWidth={currentView === "today" ? 2.5 : 2} />}
            active={currentView === "today"}
            onClick={() => setCurrentView("today")}
          />
          <NavItem
            label="Plan"
            icon={<Calendar size={24} strokeWidth={currentView === "plan" ? 2.5 : 2} />}
            active={currentView === "plan"}
            onClick={() => setCurrentView("plan")}
          />
          <NavItem
            label="Pantry"
            icon={<Archive size={24} strokeWidth={currentView === "pantry" ? 2.5 : 2} />}
            active={currentView === "pantry"}
            onClick={() => setCurrentView("pantry")}
          />
          <NavItem
            label="Recipes"
            icon={<BookOpen size={24} strokeWidth={currentView === "recipes" ? 2.5 : 2} />}
            active={currentView === "recipes"}
            onClick={() => setCurrentView("recipes")}
          />
          <NavItem
            label="Family"
            icon={<Users size={24} strokeWidth={currentView === "family" ? 2.5 : 2} />}
            active={currentView === "family"}
            onClick={() => setCurrentView("family")}
          />
        </nav>
      ) : null}

      <style>{`
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>
    </div>
  );
}
