/**
 * HouseholdSwitcher - Phase 6.3
 *
 * Dropdown to switch between multiple households.
 * Reads/writes ?household=<id> in the URL and fetches from GET /households/mine.
 */

import { useEffect, useState } from 'react';

// Tiny helper: read/set ?household=<id> in the URL
function useActiveHousehold() {
  // Read from URLSearchParams
  const params = new URLSearchParams(window.location.search);
  const initial = params.get('household') || '';

  const [active, setActive] = useState(initial);

  function selectHousehold(nextId: string) {
    setActive(nextId);
    const newParams = new URLSearchParams(window.location.search);
    newParams.set('household', nextId);
    const newUrl = window.location.pathname + '?' + newParams.toString();
    window.history.replaceState(null, '', newUrl);

    // Dispatch custom event for Dashboard to listen
    window.dispatchEvent(new Event('householdChanged'));
  }

  return { activeHouseholdId: active, selectHousehold };
}

async function fetchMyHouseholds() {
  const base = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
  const res = await fetch(`${base}/api/v1/households/mine`, {
    credentials: 'include',
  });
  if (!res.ok) {
    throw new Error(`households/mine failed: ${res.status}`);
  }
  return res.json();
}

export default function HouseholdSwitcher() {
  const { activeHouseholdId, selectHousehold } = useActiveHousehold();

  const [list, setList] = useState<
    Array<{ household_id: string; name: string; role: string }>
  >([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMyHouseholds()
      .then((arr) => {
        setList(arr);
        // If we didn't already have ?household= set, default to first
        if (!activeHouseholdId && arr.length > 0) {
          selectHousehold(arr[0].household_id);
        }
      })
      .catch((e: any) => {
        console.error(e);
        setError(String(e.message || e));
      });
    // We intentionally don't include activeHouseholdId/selectHousehold here,
    // because we only want to load the list once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div className="rounded-lg bg-card border border-border text-red-400 text-[11px] px-3 py-2 font-mono">
        {error}
      </div>
    );
  }

  const active = list.find((h) => h.household_id === activeHouseholdId);

  return (
    <div className="relative text-left">
      <button
        className="rounded-lg bg-card border border-border text-foreground text-sm px-3 py-2 flex items-center gap-2 hover:bg-muted transition-colors"
        onClick={() => setOpen(!open)}
      >
        <span>{active ? active.name : 'Select household'}</span>
        {active ? (
          <span className="text-[10px] text-muted-foreground bg-muted px-2 py-1 rounded-full border border-border">
            {active.role}
          </span>
        ) : null}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-56 rounded-xl bg-card border border-border shadow-lg p-2 flex flex-col gap-1 z-50">
          {list.map((h) => (
            <button
              key={h.household_id}
              className={`w-full flex items-center justify-between text-left text-sm px-3 py-2 rounded-lg hover:bg-muted text-foreground transition-colors ${
                h.household_id === activeHouseholdId
                  ? 'outline outline-1 outline-border bg-muted/50'
                  : ''
              }`}
              onClick={() => {
                selectHousehold(h.household_id);
                setOpen(false);
              }}
            >
              <span className="flex flex-col">
                <span className="text-foreground text-sm leading-tight">
                  {h.name}
                </span>
                <span className="text-[10px] text-muted-foreground leading-tight">
                  {h.household_id}
                </span>
              </span>
              <span className="text-[10px] text-muted-foreground bg-muted px-2 py-1 rounded-full border border-border">
                {h.role}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
