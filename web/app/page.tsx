import { Suspense } from "react";
import PredictForm from "@/app/components/PredictForm";
import DolarSection from "@/app/components/DolarSection";
import OportunidadesSection from "@/app/components/OportunidadesSection";
import VehiculosSection from "@/app/components/VehiculosSection";

// ── Skeletons ─────────────────────────────────────────────────────────────────

function DolarSkeleton() {
  return (
    <div className="flex flex-wrap gap-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="h-16 w-36 rounded-lg bg-slate-200 animate-pulse" />
      ))}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 overflow-hidden">
      <div className="h-14 bg-slate-100 border-b border-slate-200" />
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-12 border-b border-slate-100 animate-pulse bg-white flex items-center px-4 gap-4">
          <div className="h-5 w-20 rounded-md bg-slate-200" />
          <div className="h-4 w-32 rounded bg-slate-100" />
          <div className="h-4 w-10 rounded bg-slate-100" />
          <div className="ml-auto h-4 w-28 rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white text-slate-900">

      {/* ── Navbar ────────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/icon.svg" alt="TasaJusta" width={34} height={34} className="rounded-xl" />
            <span className="font-bold text-lg text-brand-500 tracking-tight">TasaJusta</span>
          </div>
          <div className="flex items-center gap-6 text-sm font-medium text-slate-500">
            <a href="#cotizador" className="hover:text-brand-500 transition-colors">Cotizador</a>
            <a href="#mercado"   className="hover:text-brand-500 transition-colors">Mercado</a>
            <a href="#oportunidades" className="hidden sm:inline hover:text-brand-500 transition-colors">
              Oportunidades
            </a>
          </div>
        </div>
      </nav>

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="bg-slate-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-14 lg:py-20">
          <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 items-start">

            {/* Texto izquierdo */}
            <div className="lg:pt-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 border border-brand-200 text-xs text-brand-600 font-semibold mb-5">
                <span className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-pulse" />
                Datos actualizados semanalmente
              </div>

              <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 leading-[1.15] mb-4">
                Sabé cuánto<br />
                <span className="text-brand-500">vale</span> tu auto.
              </h1>

              <p className="text-slate-500 text-lg leading-relaxed max-w-md mb-10">
                Analizamos publicaciones reales del mercado argentino y cruzamos el precio con el dólar blue para darte una estimación honesta.
              </p>

              {/* Steps */}
              <div className="space-y-3">
                {[
                  { n: "1", label: "Analizamos ofertas reales" },
                  { n: "2", label: "Un modelo ML analiza precio, año, km y dólar blue" },
                  { n: "3", label: "Obtenés el valor justo en pesos y en USD" },
                ].map(({ n, label }) => (
                  <div key={n} className="flex items-center gap-3">
                    <span className="w-7 h-7 rounded-full bg-brand-500 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
                      {n}
                    </span>
                    <p className="text-sm text-slate-600">{label}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Formulario — tarjeta flotante */}
            <div id="cotizador" className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
              <PredictForm />
            </div>
          </div>
        </div>
      </section>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-6 py-14 space-y-14">

        {/* Dólar */}
        <Suspense fallback={<DolarSkeleton />}>
          <DolarSection />
        </Suspense>

        {/* Oportunidades */}
        <div id="oportunidades">
          <Suspense fallback={<TableSkeleton />}>
            <OportunidadesSection />
          </Suspense>
        </div>

        {/* Mercado */}
        <section id="mercado">
          <Suspense fallback={<TableSkeleton />}>
            <VehiculosSection />
          </Suspense>
        </section>

      </main>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="bg-brand-900 text-white mt-8">
        <div className="max-w-7xl mx-auto px-6 py-10">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6 mb-6">
            <div className="flex items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/icon.svg" alt="" width={32} height={32} className="rounded-xl opacity-90" />
              <div>
                <p className="font-bold text-white">TasaJusta</p>
                <p className="text-xs text-brand-300 mt-0.5">Inteligencia de precios para el mercado de usados argentino</p>
              </div>
            </div>
            <div className="flex flex-col sm:items-end gap-1 text-xs text-brand-300">
              <span>Datos Reales + Bluelytics</span>
              <span>Modelo ML actualizado semanalmente</span>
            </div>
          </div>
          <div className="border-t border-brand-700 pt-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-brand-400">
            <span>© {new Date().getFullYear()} TasaJusta. Todos los derechos reservados.</span>
            <span>
              Desarrollado por{" "}
              <a
                href="https://rolphy.dev"
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-200 hover:text-white transition-colors font-medium"
              >
                Matías Lucero
              </a>
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
