import { Suspense } from "react";
import PredictForm from "@/app/components/PredictForm";
import DolarSection from "@/app/components/DolarSection";
import VehiculosSection from "@/app/components/VehiculosSection";

// ── Skeletons para las secciones que cargan datos ──────────────────────────

function DolarSkeleton() {
  return (
    <div className="mb-10">
      <div className="flex items-center gap-3 mb-4">
        <div className="h-3 w-36 rounded bg-gray-800 animate-pulse" />
        <div className="flex-1 h-px bg-gray-800" />
      </div>
      <div className="flex flex-wrap gap-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-16 w-36 rounded-lg bg-gray-800/60 animate-pulse" />
        ))}
      </div>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="h-3 w-40 rounded bg-gray-800 animate-pulse" />
        <div className="flex-1 h-px bg-gray-800" />
      </div>
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <div className="h-14 bg-gray-900/60 border-b border-gray-800" />
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-12 border-b border-gray-800/50 animate-pulse bg-gray-900/20 flex items-center px-4 gap-4">
            <div className="h-5 w-20 rounded-md bg-gray-800" />
            <div className="h-4 w-32 rounded bg-gray-800" />
            <div className="h-4 w-10 rounded bg-gray-800" />
            <div className="ml-auto h-4 w-28 rounded bg-gray-800" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── SVG silueta de auto ────────────────────────────────────────────────────

function CarSilhouette({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 520 180" fill="currentColor" className={className} aria-hidden>
      {/* Cuerpo */}
      <path d="M480 130 L480 108 C480 100 474 94 466 94 L440 94 L400 56 C392 46 378 40 364 40 L160 40 C146 40 132 46 124 56 L84 94 L54 94 C46 94 40 100 40 108 L40 130 Z" />
      {/* Ventanas */}
      <path d="M158 88 L184 50 C186 46 190 44 194 44 L254 44 L254 88 Z" opacity="0.45" />
      <path d="M262 44 L360 44 C368 44 376 48 382 56 L410 88 L262 88 Z" opacity="0.45" />
      {/* Ruedas */}
      <circle cx="142" cy="136" r="32" />
      <circle cx="142" cy="136" r="16" opacity="0.35" />
      <circle cx="378" cy="136" r="32" />
      <circle cx="378" cy="136" r="16" opacity="0.35" />
      {/* Faros */}
      <rect x="42" y="108" width="14" height="8" rx="4" opacity="0.7" />
      <rect x="464" y="108" width="14" height="8" rx="4" opacity="0.7" />
    </svg>
  );
}

// ── Página ─────────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">

      {/* ── Navbar ── */}
      <nav className="sticky top-0 z-50 border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-1.5 h-5 rounded-full bg-gradient-to-b from-emerald-400 to-cyan-500" />
            <span className="font-bold tracking-tight text-white">TasaJusta</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-gray-500">
            <a href="#cotizador" className="hover:text-gray-300 transition-colors">Cotizador</a>
            <a href="#mercado"   className="hover:text-gray-300 transition-colors">Mercado</a>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative overflow-hidden bg-gray-950 border-b border-gray-800/60">

        {/* Fondo: gradientes + grid sutil */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_60%_-10%,rgba(16,185,129,0.12),transparent)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_10%_80%,rgba(6,182,212,0.07),transparent)]" />
        <div className="absolute inset-0"
          style={{ backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "32px 32px" }}
        />

        <div className="relative max-w-7xl mx-auto px-6 pt-20 pb-0">
          <div className="flex flex-col lg:flex-row items-start lg:items-center gap-10">

            {/* Texto */}
            <div className="flex-1 lg:pb-20">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-800/60 bg-emerald-950/40 text-xs text-emerald-400 font-medium mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Datos actualizados semanalmente
              </div>

              <h1 className="text-5xl lg:text-6xl font-bold tracking-tight leading-tight text-white mb-4">
                Sabé cuánto <br />
                <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                  vale tu auto.
                </span>
              </h1>

              <p className="text-gray-400 text-lg leading-relaxed max-w-xl mb-8">
                TasaJusta analiza publicaciones reales del mercado argentino y cruza el precio con el dólar blue para darte una estimación honesta.
              </p>

              {/* Cómo funciona */}
              <div className="flex flex-col sm:flex-row gap-3">
                {[
                  { n: "1", label: "Scrapeamos publicaciones reales de DeRuedas" },
                  { n: "2", label: "Un modelo ML analiza precio, año, km y dólar" },
                  { n: "3", label: "Obtenés el valor justo en pesos y en USD blue" },
                ].map(({ n, label }) => (
                  <div key={n} className="flex items-start gap-2.5 flex-1 rounded-lg p-3 border border-gray-800 bg-gray-900/40">
                    <span className="w-5 h-5 rounded-full bg-emerald-900/60 border border-emerald-800 text-emerald-400 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {n}
                    </span>
                    <p className="text-xs text-gray-400 leading-relaxed">{label}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Car SVG */}
            <div className="w-full lg:w-[480px] lg:flex-shrink-0 flex items-end justify-center lg:justify-end self-end">
              <div className="relative w-full max-w-md">
                {/* Glow debajo del auto */}
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 w-64 h-6 rounded-full bg-emerald-500/10 blur-xl" />
                <CarSilhouette className="w-full text-emerald-950 drop-shadow-[0_0_40px_rgba(16,185,129,0.15)]" />
              </div>
            </div>
          </div>
        </div>

        {/* Fade hacia el contenido */}
        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-gray-950 to-transparent" />
      </section>

      {/* ── Main content ── */}
      <main className="max-w-7xl mx-auto px-6 py-12 space-y-12">

        {/* Cotizador */}
        <section id="cotizador">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">
              Cotizador
            </h2>
            <div className="flex-1 h-px bg-gray-800" />
          </div>
          <PredictForm />
        </section>

        {/* Dólar — streamed */}
        <Suspense fallback={<DolarSkeleton />}>
          <DolarSection />
        </Suspense>

        {/* Vehículos — streamed */}
        <section id="mercado">
          <Suspense fallback={<TableSkeleton />}>
            <VehiculosSection />
          </Suspense>
        </section>

      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-gray-800/60 py-8 mt-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-600">
          <div className="flex items-center gap-2">
            <div className="w-1 h-4 rounded-full bg-gradient-to-b from-emerald-500 to-cyan-500" />
            <span className="font-semibold text-gray-400">TasaJusta</span>
            <span>— Inteligencia de precios para el mercado de usados argentino</span>
          </div>
          <div className="flex gap-4">
            <span>Datos: DeRuedas + bluelytics</span>
            <span>·</span>
            <span>Actualizado semanalmente</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
