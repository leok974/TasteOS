/**
 * Dashboard Page - Phase 6.1/6.3
 *
 * Household nutrition dashboard showing per-member nutrition status,
 * goals, violations, and suggestions.
 */

import { useEffect, useState } from 'react';
import HouseholdSwitcher from '../components/HouseholdSwitcher';

// TODO: centralize in lib/api later
async function fetchTodayNutrition(householdId: string) {
  const base = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
  const res = await fetch(
    `${base}/api/v1/nutrition/today?household_id=${encodeURIComponent(
      householdId,
    )}`,
    {
      credentials: 'include',
    },
  );

  if (!res.ok) {
    throw new Error(`nutrition fetch failed: ${res.status}`);
  }
  return res.json();
}

interface StatusChipProps {
  label: string;
  tone: 'good' | 'warn' | 'alert';
}

function StatusChip({ label, tone }: StatusChipProps) {
  const toneClasses =
    tone === 'good'
      ? 'bg-emerald-500/30 text-emerald-300 border-emerald-600/40'
      : tone === 'warn'
        ? 'bg-yellow-500/30 text-yellow-300 border-yellow-600/40'
        : 'bg-red-500/30 text-red-300 border-red-600/40';

  return (
    <span className={`text-[10px] px-2 py-1 rounded-full border ${toneClasses}`}>
      {label}
    </span>
  );
}

interface MemberCardProps {
  member: {
    user_id: string;
    name: string;
    goals: {
      calories_target: number;
      protein_target_g: number;
      allergies?: string[];
    };
    day_intake: {
      calories: number;
      protein_g: number;
      carbs_g: number;
      fat_g: number;
    };
    status: {
      calories_ok: boolean;
      protein_ok: boolean;
      allergy_violations?: Array<{
        recipe_id: string;
        ingredient: string;
        severity: string;
      }>;
    };
    suggestions?: string[];
  };
}

function MemberCard({ member }: MemberCardProps) {
  return (
    <div className="rounded-2xl bg-surface-card p-4 shadow-sm border border-border flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-base font-medium text-white">{member.name}</div>
          <div className="text-xs text-muted-foreground">
            Target: {member.goals.calories_target} kcal / {member.goals.protein_target_g}g protein
          </div>
        </div>

        <div className="flex flex-wrap gap-1 text-xs">
          <StatusChip
            label={member.status.calories_ok ? 'Calories OK' : 'Calories high'}
            tone={member.status.calories_ok ? 'good' : 'warn'}
          />
          <StatusChip
            label={member.status.protein_ok ? 'Protein OK' : 'Protein low'}
            tone={member.status.protein_ok ? 'good' : 'warn'}
          />
          {member.status.allergy_violations && member.status.allergy_violations.length > 0 && (
            <StatusChip label="Allergy risk" tone="alert" />
          )}
        </div>
      </div>

      <div className="text-sm text-white/90 space-y-1">
        <div className="flex justify-between">
          <span>Calories</span>
          <span>
            {member.day_intake.calories} / {member.goals.calories_target}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Protein</span>
          <span>
            {member.day_intake.protein_g}g / {member.goals.protein_target_g}g
          </span>
        </div>
        <div className="flex justify-between">
          <span>Carbs</span>
          <span>{member.day_intake.carbs_g}g</span>
        </div>
        <div className="flex justify-between">
          <span>Fat</span>
          <span>{member.day_intake.fat_g}g</span>
        </div>
      </div>

      {member.suggestions && member.suggestions.length > 0 && (
        <div className="rounded-lg bg-surface-muted text-xs text-muted-foreground p-3 leading-relaxed">
          {member.suggestions.join(' ')}
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeHouseholdId, setActiveHouseholdId] = useState<string>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('household') || '';
  });

  // Watch the URL for changes to ?household= and update state
  useEffect(() => {
    const handleHouseholdChange = () => {
      const p = new URLSearchParams(window.location.search);
      setActiveHouseholdId(p.get('household') || '');
    };

    window.addEventListener('householdChanged', handleHouseholdChange);
    window.addEventListener('popstate', handleHouseholdChange);

    return () => {
      window.removeEventListener('householdChanged', handleHouseholdChange);
      window.removeEventListener('popstate', handleHouseholdChange);
    };
  }, []);

  useEffect(() => {
    if (!activeHouseholdId) return;

    fetchTodayNutrition(activeHouseholdId)
      .then(setData)
      .catch((err) => {
        console.error(err);
        setError(String(err));
      });
  }, [activeHouseholdId]);

  if (error) {
    return <main className="bg-app min-h-screen p-6 text-red-400 text-sm font-mono">{error}</main>;
  }

  if (!activeHouseholdId) {
    return (
      <main className="bg-app min-h-screen p-6 text-muted-foreground text-sm">
        Select a household to view the dashboard…
      </main>
    );
  }

  if (!data) {
    return <main className="bg-app min-h-screen p-6 text-muted-foreground text-sm">Loading dashboard…</main>;
  }

  return (
    <main className="bg-app min-h-screen p-6 flex flex-col gap-6">
      <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white">Today's Nutrition</h1>
          <p className="text-sm text-muted-foreground">
            Household {data.household_id} — {data.date}
          </p>
        </div>

        {/* Real HouseholdSwitcher (Phase 6.3) */}
        <HouseholdSwitcher />
      </header>

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data.members.map((m: any) => (
          <MemberCard key={m.user_id} member={m} />
        ))}
      </section>
    </main>
  );
}
