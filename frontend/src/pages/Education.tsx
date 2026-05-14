import { useEffect, useState } from 'react'

interface Concept {
  slug: string
  name: string
  short: string
  explanation: string
  how_we_use_it: string
  thresholds: Record<string, number>
  category: string
}

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

const CATEGORY_LABELS: Record<string, string> = {
  momentum: 'Momentum',
  trend: 'Trend',
  volatility: 'Volatility',
  performance: 'Performance',
}

export default function Education() {
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/education/concepts`, { credentials: 'include' })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<Concept[]>
      })
      .then((data) => {
        setConcepts(data)
        if (data.length > 0) setSelected(data[0].slug)
      })
      .catch((e: unknown) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  const active = concepts.find((c) => c.slug === selected)

  if (loading) {
    return (
      <div data-testid="education-loading" className="p-6 text-[var(--kt-on-surface-variant)]">
        Loading concepts...
      </div>
    )
  }

  if (error) {
    return (
      <div data-testid="education-error" className="p-6 text-[var(--kt-tertiary-container)]">
        Failed to load: {error}
      </div>
    )
  }

  const grouped = Object.entries(CATEGORY_LABELS).reduce<Record<string, Concept[]>>(
    (acc, [cat]) => {
      acc[cat] = concepts.filter((c) => c.category === cat)
      return acc
    },
    {},
  )

  return (
    <div data-testid="education-page" className="flex h-full gap-6">
      {/* Sidebar */}
      <aside className="w-64 shrink-0">
        <h2 className="text-lg font-bold text-[var(--kt-on-surface)] mb-4">Trading Glossary</h2>
        {Object.entries(grouped).map(([cat, items]) =>
          items.length === 0 ? null : (
            <div key={cat} className="mb-4">
              <p className="label-terminal text-[var(--kt-primary-container)] mb-2">
                {CATEGORY_LABELS[cat]}
              </p>
              {items.map((concept) => (
                <button
                  key={concept.slug}
                  data-testid={`concept-nav-${concept.slug}`}
                  onClick={() => setSelected(concept.slug)}
                  className={`w-full text-left px-3 py-2 rounded text-sm mb-1 transition-colors ${
                    selected === concept.slug
                      ? 'bg-[var(--kt-surface-container-highest)] text-[var(--kt-on-surface)] border-l-2 border-[var(--kt-primary-container)]'
                      : 'text-[var(--kt-on-surface-variant)] hover:bg-[var(--kt-surface-container-high)]'
                  }`}
                >
                  {concept.name}
                </button>
              ))}
            </div>
          ),
        )}
      </aside>

      {/* Detail panel */}
      <main className="flex-1 min-w-0">
        {active ? (
          <div data-testid={`concept-detail-${active.slug}`} className="space-y-6">
            <div>
              <span className="label-terminal text-[var(--kt-primary-container)] bg-[var(--kt-primary-container)]/10 px-2 py-1 rounded">
                {CATEGORY_LABELS[active.category] ?? active.category}
              </span>
              <h1 className="text-2xl font-bold text-[var(--kt-on-surface)] mt-2">{active.name}</h1>
              <p className="text-[var(--kt-on-surface-variant)] mt-1">{active.short}</p>
            </div>

            <section>
              <h3 className="label-terminal text-[var(--kt-on-surface-variant)] mb-2">
                What it is
              </h3>
              <p className="text-[var(--kt-on-surface-variant)] leading-relaxed">{active.explanation}</p>
            </section>

            {Object.keys(active.thresholds).length > 0 && (
              <section>
                <h3 className="label-terminal text-[var(--kt-on-surface-variant)] mb-2">
                  Key Levels
                </h3>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(active.thresholds).map(([k, v]) => (
                    <div key={k} className="bg-[var(--kt-surface-container-high)] rounded px-3 py-2 text-sm">
                      <span className="text-[var(--kt-on-surface-variant)] capitalize">{k.replace(/_/g, ' ')}: </span>
                      <span className="text-[var(--kt-on-surface)] font-semibold font-mono">{v}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section>
              <h3 className="label-terminal text-[var(--kt-on-surface-variant)] mb-2">
                How this bot uses it
              </h3>
              <p className="text-[var(--kt-on-surface)] leading-relaxed bg-[var(--kt-surface-container-low)] rounded p-4 border-l-2 border-[var(--kt-primary-container)]">
                {active.how_we_use_it}
              </p>
            </section>
          </div>
        ) : (
          <p className="text-[var(--kt-on-surface-variant)]">Select a concept from the left.</p>
        )}
      </main>
    </div>
  )
}
