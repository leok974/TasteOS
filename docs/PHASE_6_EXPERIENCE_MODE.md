# Phase 6 — Experience Mode  
Date: 2025-10-28  
Status: backend stable / CI enforced / move to product demo mode

## Goal
Turn TasteOS from "working backend with tests" into "shareable product demo":
- A real dashboard UI that understands households, nutrition, and invites.
- A flow that shows how families join and live inside TasteOS.
- A landing page you can show to recruiters/judges and in a 60s video.

Phase 6 is front-end heavy, using the existing backend as the source of truth.

---

## Phase 6 Subphases

### 6.1 Household Dashboard

**Purpose**  
Give the owner (and members) a daily view:
- Am I within my nutrition profile?
- Did I violate allergies/intolerances?
- What should I eat next?

This is the "why TasteOS matters" screen for demos.

#### Backend
**Endpoint**
`GET /api/v1/nutrition/today?household_id=<id>`

**Auth rules**
- Requesting user must be a member of that household.
- A non-member gets 403.
- Later: owner-only fields can be flagged if needed, but v0 we just return per-member summaries.

**Response shape (planned)**
```json
{
  "household_id": "abc123",
  "date": "2025-10-28",
  "members": [
    {
      "user_id": "u_01",
      "name": "Leo",
      "goals": {
        "calories_target": 2400,
        "protein_target_g": 180,
        "allergies": ["shellfish"]
      },
      "day_intake": {
        "calories": 1720,
        "protein_g": 102,
        "carbs_g": 140,
        "fat_g": 60
      },
      "status": {
        "calories_ok": true,
        "protein_ok": false,
        "allergy_violations": [
          {
            "recipe_id": "shrimp_rasta_pasta",
            "ingredient": "shrimp",
            "severity": "high"
          }
        ]
      },
      "suggestions": [
        "Add a high-protein snack (Greek yogurt, 20g protein)",
        "Avoid shellfish in dinner tonight"
      ]
    }
  ]
}
```

**To build:**
- Extend the existing nutrition service to aggregate for "today" per member.
- Include status and suggestions, even if suggestions are initially stubbed with heuristics.
- Return empty arrays instead of nulls to keep the frontend simple.

#### Frontend

**Route**  
`/dashboard?household=<id>`

**Layout (shadcn/Tailwind)**
- One `<Card>` per member.
- Each card shows:
  - Name
  - Compliance chips
  - Macro totals vs targets
  - "Next step" suggestion

**Rough component sketch:**
```tsx
// apps/web/src/pages/Dashboard.tsx
// PSEUDO-CODE / SCAFFOLD TARGET

export function DashboardPage() {
  // 1. read household from query or context
  // 2. fetch /api/v1/nutrition/today?household_id=<id>
  // 3. render cards

  return (
    <main className="p-6 flex flex-col gap-6">
      <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white">
            Today's Nutrition
          </h1>
          <p className="text-sm text-muted-foreground">
            Household summary for Oct 28, 2025
          </p>
        </div>

        {/* household switcher lives here in 6.3 */}
        <HouseholdSwitcher />
      </header>

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* members.map(...) */}
        <MemberCard />
        <MemberCard />
        <MemberCard />
      </section>
    </main>
  );
}

// Card concept
function MemberCard() {
  return (
    <div className="rounded-2xl bg-surface-card p-4 shadow-sm border border-border flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-base font-medium text-white">Leo</div>
          <div className="text-xs text-muted-foreground">
            Target: 2400 kcal / 180g protein
          </div>
        </div>

        <div className="flex flex-wrap gap-1 text-xs">
          {/* status chips */}
          <StatusChip label="Calories OK" tone="good" />
          <StatusChip label="Protein low" tone="warn" />
          <StatusChip label="Allergy risk" tone="alert" />
        </div>
      </div>

      <div className="text-sm text-white/90">
        <div className="flex justify-between">
          <span>Calories</span>
          <span>1720 / 2400</span>
        </div>
        <div className="flex justify-between">
          <span>Protein</span>
          <span>102g / 180g</span>
        </div>
        <div className="flex justify-between">
          <span>Carbs</span>
          <span>140g</span>
        </div>
        <div className="flex justify-between">
          <span>Fat</span>
          <span>60g</span>
        </div>
      </div>

      <div className="rounded-lg bg-surface-muted text-xs text-muted-foreground p-3 leading-relaxed">
        Suggestion: Add a high-protein snack (Greek yogurt, 20g protein).  
        Avoid shellfish in dinner tonight.
      </div>
    </div>
  );
}
```

**Visual language:**
- Dark-first (like ApplyLens).
- Surfaces:
  - `bg-surface-card` (card background)
  - `bg-surface-muted` (sub-panels / callouts)
  - thin `border-border` outline, `rounded-2xl`
- StatusChip should be tiny, pill-shaped, 11–12px text.

**Acceptance for 6.1**
- `/dashboard` loads with hardcoded mock data first → then real API.
- HouseholdSwitcher shows the active household name.
- Cards render one per member.

---

### 6.2 Household Invite UX

**Purpose**  
Show that TasteOS is "for families," not just single-user.

This is the story we demo:
1. Owner generates an invite code for the household.
2. Another user pastes that code to join.

#### Backend

We already have:
- Owner can create invites (token-based).
- Another user can join via token.
- `_require_owner()` centralizes "only owners can invite."

In Phase 6 we expose those flows in UI.

**Endpoints in use**

**`POST /households/invite`**
- Body: `{ "household_id": "<id>" }`
- Auth: must be owner.
- Response:
```json
{
  "invite_token": "abc123-secure-token",
  "household_id": "abc123",
  "expires_at": "2025-11-01T00:00:00Z"
}
```

**`POST /households/join`**
- Body: `{ "token": "abc123-secure-token" }`
- Auth: caller becomes a member of that household if token valid.

#### Frontend

**Owner View: InvitePage (Generate)**
```tsx
// /invite (owner mode)
function InviteOwnerPage() {
  // button: "Generate invite link"
  // show returned token in a CopyField component

  return (
    <main className="p-6 max-w-md mx-auto flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-white">
        Invite someone to your household
      </h1>
      <p className="text-sm text-muted-foreground">
        They'll get access to shared meals, allergies, and nutrition tracking.
      </p>

      <button className="btn-primary w-full">
        Generate invite link
      </button>

      {/* after POST /households/invite */}
      <div className="rounded-xl bg-surface-card border border-border p-4 flex flex-col gap-2">
        <div className="text-xs text-muted-foreground">
          Share this code:
        </div>
        <code className="text-white text-sm font-mono break-all">
          abc123-secure-token
        </code>
        <button className="btn-secondary text-xs self-start">
          Copy
        </button>
      </div>
    </main>
  );
}
```

**Invitee View: JoinPage (Accept)**
```tsx
// /join
function JoinHouseholdPage() {
  // form: paste code, submit → POST /households/join

  return (
    <main className="p-6 max-w-md mx-auto flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-white">
        Join a household
      </h1>

      <label className="flex flex-col gap-2 text-sm">
        <span className="text-muted-foreground">
          Invite code
        </span>
        <input
          className="rounded-lg bg-surface-card border border-border text-white p-3 text-sm font-mono"
          placeholder="paste-your-code-here"
        />
      </label>

      <button className="btn-primary w-full">
        Join household
      </button>

      <p className="text-[11px] text-muted-foreground leading-relaxed">
        When you join, you'll share nutrition insights and preferences
        with the household owner.
      </p>
    </main>
  );
}
```

**Acceptance for 6.2**
- Owner can generate a token in UI and copy it.
- Invitee can paste token and call join.
- 403 surfaces as a toast: "Only owners can invite."

---

### 6.3 Household Switcher

**Purpose**  
Multi-tenant awareness. You can belong to multiple households (e.g. "My Apartment", "Parents", "Partner"). You can pivot context in the UI.

#### Backend

**Endpoint**  
`GET /api/v1/households/mine`

**Response shape (planned)**
```json
[
  {
    "household_id": "abc123",
    "name": "My Apartment",
    "role": "owner"
  },
  {
    "household_id": "def456",
    "name": "Parents",
    "role": "member"
  }
]
```

**Implementation notes:**
- Join flow should update membership so the invitee now appears here.
- `role` is either "owner" or "member".

#### Frontend

**Component**  
`<HouseholdSwitcher />` in the navbar / dashboard header.

**Behavior:**
- Shows current household name.
- Clicking opens a dropdown of all households.
- Selecting one updates `?household=<id>` in the URL (and forces a refetch of dashboard data).

**Sketch:**
```tsx
function HouseholdSwitcher() {
  // state: list of households from /api/v1/households/mine
  // state: activeHouseholdId (from URL or first in list)

  return (
    <div className="relative">
      <button className="rounded-lg bg-surface-card border border-border text-white text-sm px-3 py-2 flex items-center gap-2">
        <span>My Apartment</span>
        <ChevronDownIcon className="w-4 h-4 text-muted-foreground" />
      </button>

      {/* dropdown menu */}
      {/* each row: household.name + role chip */}
    </div>
  );
}
```

**Acceptance for 6.3**
- Switcher renders on dashboard header.
- Switching households updates dashboard without a full page reload.

---

### 6.4 Landing Page

**Purpose**  
You need a public face. Phase 6 ships a marketing surface so someone can "get" TasteOS in 10 seconds.

**Route**  
`/` (public marketing surface, not gated)

**Sections**

**Hero**
- Tagline: "TasteOS — shared nutrition, shared health."
- CTA button: "See Dashboard Demo" → `/dashboard?household=<id>`

**Value props**
- "See everyone's nutrition at a glance"
- "Auto-track allergies and risks"
- "Invite your household, instantly"
- Screenshot frame or inline demo card mock

**Sketch:**
```tsx
// apps/web/src/pages/LandingPage.tsx
export function LandingPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-black to-surface-card text-white p-8 flex flex-col gap-16">
      <section className="max-w-3xl flex flex-col gap-6">
        <h1 className="text-3xl font-semibold leading-tight">
          TasteOS
        </h1>
        <p className="text-lg text-muted-foreground leading-relaxed">
          Shared nutrition intelligence for real households.
          Track goals. Catch allergy risks. Plan better meals.
        </p>
        <div className="flex flex-col sm:flex-row gap-3">
          <a
            className="btn-primary px-4 py-2 text-sm font-medium"
            href="/dashboard"
          >
            See the dashboard
          </a>
          <a
            className="btn-secondary px-4 py-2 text-sm font-medium"
            href="/join"
          >
            Join a household
          </a>
        </div>
      </section>

      <section className="max-w-4xl grid gap-6 sm:grid-cols-3">
        <ValueCard title="Family view" body="Daily calories, protein, and allergy alerts for everyone you care about." />
        <ValueCard title="Instant invites" body="Add your partner, roommates, or kids with one secure code." />
        <ValueCard title="Respect boundaries" body="Households are isolated. Only members see household data." />
      </section>

      <section className="max-w-4xl">
        <DemoFrame />
      </section>

      <footer className="text-[11px] text-muted-foreground">
        © 2025 TasteOS. Built for real families.
      </footer>
    </main>
  )
}
```

**Acceptance for 6.4**
- `/` renders without auth
- There is a visible CTA to `/dashboard` and `/join`

---

### 6.5 Infrastructure Polish

**Goal**  
Get production-ready hygiene so you can ship this and record the demo without your stack exploding.

**Tasks**

1. **Add health endpoint**
   - `GET /api/ready`
   - returns: `{ "status": "ok", "db": "ok" }`
   - CI smoke test uses this.

2. **Tighten pytest defaults**
   - In CI: `pytest --maxfail=1 --disable-warnings` (keeps runs fast and loud)

3. **Pre-commit tooling**
   - ruff (lint)
   - black (format)
   - staged hook for `apps/api/` + optionally `apps/web/`

4. **Watchtower label**
   - Ensure API / Web containers have `WATCHTOWER_LABEL=tasteos` or equivalent so only these images auto-roll.

5. **Frontend env hygiene**
   - Add `apps/web/.env.sample`:
     ```
     VITE_API_BASE=http://localhost:8000
     ```

6. **CI marker**
   - Add pytest marker `phase6` and enforce it in `.github/workflows/test.yml`
   - Version tag: `v0.6.0-dashboard`

**Acceptance for 6.5**
- `GET /api/ready` exists and returns 200.
- Repo has pre-commit config for ruff/black.
- `.env.sample` exists for web.
- CI runs pytest with stricter flags and includes phase6 in the matrix.

---

### 6.6 Demo + Distribution

**Goal**  
Ship a 60s narrative demo that shows the TasteOS loop:
1. Owner opens dashboard → sees nutrition cards for household.
2. Owner generates invite code.
3. New user pastes code to join.
4. Dashboard updates to show new member card.
5. Landing page CTA.

This is your job-hunt and hackathon asset.

**Script beats**
- "This is TasteOS. It keeps everyone in your home aligned on nutrition and allergies."
- "Here's the dashboard. Everyone in the household shows up with goals and risks."
- "I can invite someone securely with one code."
- "They paste the code and instantly join."
- "Now they're visible in our dashboard."
- "This is what shared health looks like."

We'll record UI clicks, then do ElevenLabs voiceover on top, then cut in CapCut.

**Acceptance for 6.6**
- You can screen-record a full flow:
  - `/dashboard`
  - `/invite` (owner mode)
  - `/join` (invitee mode)
  - refresh `/dashboard` to see the additional member
  - `/` landing hero
- No console errors during walkthrough.

---

## API Contract Summary (Phase 6 targets)

| Endpoint | Method | Purpose | Used By |
|----------|--------|---------|---------|
| `/api/v1/nutrition/today?household_id=<id>` | GET | Returns per-member nutrition + status | Dashboard |
| `/households/invite` | POST | Owner-only. Returns invite_token | InviteOwnerPage |
| `/households/join` | POST | Body has token. Adds caller to household | JoinHouseholdPage |
| `/api/v1/households/mine` | GET | Returns array of households { household_id, name, role } | HouseholdSwitcher |
| `/api/ready` | GET | Health/smoke. Used by CI / prod sanity check | CI |

---

## Frontend Components To Build

### DashboardPage
- Fetch `/api/v1/nutrition/today`
- Render `<MemberCard />[]`
- Include `<HouseholdSwitcher />`

### MemberCard
- Name, targets
- Status chips (good / warn / alert)
- Macros
- Suggestion box

### InviteOwnerPage
- Button → `POST /households/invite`
- Copy token UI

### JoinHouseholdPage
- Input token
- Button → `POST /households/join`
- On success → redirect `/dashboard?household=<joined>`

### HouseholdSwitcher
- Dropdown of `/api/v1/households/mine`
- Updates `?household=<id>`

### LandingPage
- Hero, value props, CTA buttons

All of these live in **dark theme** using Tailwind + shadcn/ui primitives. Reuse your existing surface tokens (`bg-surface-card`, `bg-surface-muted`, border tokens, `rounded-2xl`, etc.) so TasteOS visually matches ApplyLens.

---

## Rollout Checklist (Phase 6)

- [ ] Extend `/api/v1/nutrition/today` to return members[] shape above
- [ ] Add `GET /api/ready`
- [ ] Add `GET /api/v1/households/mine`
- [ ] DashboardPage + MemberCard scaffolded in apps/web
- [ ] HouseholdSwitcher with dropdown + role chip
- [ ] InviteOwnerPage (token generator / copy UI)
- [ ] JoinHouseholdPage (paste token -> join)
- [ ] LandingPage with hero + CTAs
- [ ] `.env.sample` with `VITE_API_BASE`
- [ ] pre-commit with ruff + black
- [ ] GH Actions:
  - run pytest with `--maxfail=1 --disable-warnings`
  - require phase6 marker
- [ ] Tag release `v0.6.0-dashboard`
