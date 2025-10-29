/**
 * Landing Page - Phase 6.4
 *
 * Public marketing page with hero, value props, and CTAs.
 * Shows demo preview of household dashboard.
 */

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-black to-card text-white p-8 flex flex-col gap-16">
      {/* HERO */}
      <section className="max-w-3xl flex flex-col gap-6">
        <h1 className="text-3xl font-semibold leading-tight text-white">TasteOS</h1>

        <p className="text-lg text-muted-foreground leading-relaxed">
          Shared nutrition intelligence for real households. Track goals. Catch allergy risks.
          Plan better meals together.
        </p>

        <div className="flex flex-col sm:flex-row gap-3">
          <a
            className="rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium text-center hover:bg-primary/90 transition-colors"
            href="/dashboard"
          >
            See the dashboard
          </a>

          <a
            className="rounded-lg bg-card border border-border text-foreground px-4 py-2 text-sm font-medium text-center hover:bg-muted transition-colors"
            href="/join"
          >
            Join a household
          </a>
        </div>

        <p className="text-[11px] text-muted-foreground leading-relaxed max-w-sm">
          TasteOS shows everyone's nutrition status, allergies, and goals in one shared view —
          without guessing or group chats.
        </p>
      </section>

      {/* VALUE PROPS */}
      <section className="max-w-4xl grid gap-6 sm:grid-cols-3">
        <ValueCard
          title="Family view"
          body="Daily calories, protein, and allergy alerts for everyone you care about."
        />
        <ValueCard
          title="Instant invites"
          body="Add your partner, roommates, or kids with one secure code. No setup drama."
        />
        <ValueCard
          title="Respect boundaries"
          body="Households are isolated. Only members see shared data."
        />
      </section>

      {/* DEMO FRAME */}
      <section className="max-w-4xl w-full">
        <DemoFrame />
      </section>

      {/* FOOTER */}
      <footer className="text-[11px] text-muted-foreground">
        © 2025 TasteOS. Built for real families.
      </footer>
    </main>
  );
}

function ValueCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl bg-card border border-border p-4 flex flex-col gap-2 shadow-sm">
      <div className="text-white text-sm font-medium">{title}</div>
      <div className="text-[13px] text-muted-foreground leading-relaxed">{body}</div>
    </div>
  );
}

function DemoFrame() {
  // For Phase 6.4 this is static. In Phase 6.6 you can replace this
  // with a screenshot or short looping clip of the dashboard.
  return (
    <div className="rounded-2xl bg-card border border-border p-4 shadow-sm flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="text-sm font-medium text-white">Household Dashboard Preview</div>
        <span className="text-[10px] text-muted-foreground bg-muted px-2 py-1 rounded-full border border-border">
          demo
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl bg-muted border border-border p-3 flex flex-col gap-2">
          <div className="text-xs text-white font-medium flex items-center justify-between">
            <span>Leo</span>
            <span className="text-[10px] text-emerald-300 bg-emerald-500/20 border border-emerald-600/40 rounded-full px-2 py-0.5">
              Calories OK
            </span>
          </div>
          <div className="text-[11px] text-muted-foreground leading-relaxed">
            1720 / 2400 kcal
            <br />
            Protein 102g / 180g
          </div>
          <div className="rounded-lg bg-black/40 text-[11px] text-muted-foreground leading-relaxed p-2 border border-border">
            Add a high-protein snack
            <br />
            Avoid shellfish tonight
          </div>
        </div>

        <div className="rounded-xl bg-muted border border-border p-3 flex flex-col gap-2">
          <div className="text-xs text-white font-medium flex items-center justify-between">
            <span>Maya</span>
            <span className="text-[10px] text-red-300 bg-red-500/20 border border-red-600/40 rounded-full px-2 py-0.5">
              Allergy risk
            </span>
          </div>
          <div className="text-[11px] text-muted-foreground leading-relaxed">
            Shrimp flagged
            <br />
            Severity: high
          </div>
          <div className="rounded-lg bg-black/40 text-[11px] text-muted-foreground leading-relaxed p-2 border border-border">
            Swap dinner protein.
            <br />
            Avoid shellfish.
          </div>
        </div>

        <div className="rounded-xl bg-muted border border-border p-3 flex flex-col gap-2">
          <div className="text-xs text-white font-medium flex items-center justify-between">
            <span>Chris</span>
            <span className="text-[10px] text-yellow-300 bg-yellow-500/20 border border-yellow-600/40 rounded-full px-2 py-0.5">
              Protein low
            </span>
          </div>
          <div className="text-[11px] text-muted-foreground leading-relaxed">
            Protein 58g / 140g
            <br />
            Calories OK
          </div>
          <div className="rounded-lg bg-black/40 text-[11px] text-muted-foreground leading-relaxed p-2 border border-border">
            Add Greek yogurt or eggs
            <br />
            before bed.
          </div>
        </div>
      </div>

      <div className="text-[11px] text-muted-foreground leading-relaxed">
        TasteOS shows nutrition, risk, and next actions for everyone in your household — in one
        place.
      </div>
    </div>
  );
}
