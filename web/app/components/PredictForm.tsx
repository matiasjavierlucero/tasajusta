"use client";

import { useState } from "react";

// Marcas y modelos conocidos por el modelo ML (los que vio en training)
const MODELOS_POR_MARCA: Record<string, string[]> = {
  Chevrolet: ["Aveo", "Captiva", "Celta", "Classic", "Cruze", "Onix", "Tracker"],
  Citroen:   ["C3", "C3 Aircross", "C4 Cactus", "C4 Grand Picaso", "C4 Lounge"],
  Fiat:      ["500", "Argo", "Cronos", "Idea", "Nuevo Palio", "Punto", "Siena"],
  Ford:      ["EcoSport", "Fiesta KD", "Focus", "Ka", "Kuga"],
  Honda:     ["City", "Civic", "CRV", "Fit", "HR V"],
  Nissan:    ["Kicks", "March", "Note", "Sentra", "Tiida", "Versa"],
  Peugeot:   ["2008", "207", "208", "308", "408"],
  Renault:   ["Clio", "Duster", "Fluence", "Sandero"],
  Toyota:    ["Corolla", "Corolla Cross", "Etios", "Hilux SW4", "Yaris"],
  Volkswagen:["Bora", "Fox", "Gol", "Gol Trend", "Golf", "Polo", "Suran", "Taos", "Tiguan", "Vento", "Voyage"],
};

const PROVINCIAS = ["Buenos Aires", "Cordoba", "Mendoza", "San Juan"];
const MARCAS     = Object.keys(MODELOS_POR_MARCA).sort();
const ANIO_MIN   = 2005;
const ANIO_MAX   = new Date().getFullYear();

// Llama al Route Handler de Next.js (mismo origen → sin CORS)
const API_URL = "/api";

type PredictResult = {
  precio_estimado_ars: number;
  modelo_usado:        string;
  dolar_blue_venta:    number | null;
  advertencia:         string | null;
};

const selectCls =
  "w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-100 " +
  "focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 " +
  "disabled:opacity-40 disabled:cursor-not-allowed transition-colors";

const labelCls = "block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5";

export default function PredictForm() {
  const [marca,     setMarca]     = useState("");
  const [modelo,    setModelo]    = useState("");
  const [provincia, setProvincia] = useState("");
  const [anio,      setAnio]      = useState("");
  const [km,        setKm]        = useState("");
  const [loading,   setLoading]   = useState(false);
  const [result,    setResult]    = useState<PredictResult | null>(null);
  const [error,     setError]     = useState<string | null>(null);

  const modelos = marca ? MODELOS_POR_MARCA[marca] ?? [] : [];
  const valid   = marca && modelo && provincia && anio && km;

  function handleMarca(m: string) {
    setMarca(m);
    setModelo("");   // resetear modelo al cambiar marca
    setResult(null);
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/predict`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          marca,
          modelo,
          provincia,
          anio:  parseInt(anio),
          km:    parseInt(km),
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Error ${res.status}`);
      }

      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  const precioUSD = result && result.dolar_blue_venta
    ? Math.round(result.precio_estimado_ars / result.dolar_blue_venta)
    : null;

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/60 overflow-hidden">

      {/* Título del formulario */}
      <div className="px-6 py-5 border-b border-gray-800 bg-gradient-to-r from-emerald-950/40 to-gray-900/40">
        <h3 className="text-base font-semibold text-white">Cotizá tu auto</h3>
        <p className="text-sm text-gray-500 mt-0.5">
          El modelo estima el precio justo según las publicaciones actuales del mercado.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">

          {/* Marca */}
          <div>
            <label className={labelCls}>Marca</label>
            <select className={selectCls} value={marca} onChange={e => handleMarca(e.target.value)}>
              <option value="">Seleccioná una marca</option>
              {MARCAS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          {/* Modelo */}
          <div>
            <label className={labelCls}>Modelo</label>
            <select
              className={selectCls}
              value={modelo}
              onChange={e => { setModelo(e.target.value); setResult(null); }}
              disabled={!marca}
            >
              <option value="">
                {marca ? "Seleccioná un modelo" : "Primero elegí la marca"}
              </option>
              {modelos.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          {/* Provincia */}
          <div>
            <label className={labelCls}>Provincia</label>
            <select
              className={selectCls}
              value={provincia}
              onChange={e => { setProvincia(e.target.value); setResult(null); }}
            >
              <option value="">Seleccioná una provincia</option>
              {PROVINCIAS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {/* Año */}
          <div>
            <label className={labelCls}>Año</label>
            <input
              type="number"
              min={ANIO_MIN}
              max={ANIO_MAX}
              placeholder={`${ANIO_MIN} – ${ANIO_MAX}`}
              className={selectCls}
              value={anio}
              onChange={e => { setAnio(e.target.value); setResult(null); }}
            />
          </div>

          {/* Km */}
          <div>
            <label className={labelCls}>Kilómetros</label>
            <input
              type="number"
              min={0}
              placeholder="Ej: 85000"
              className={selectCls}
              value={km}
              onChange={e => { setKm(e.target.value); setResult(null); }}
            />
          </div>

          {/* Botón */}
          <div className="flex items-end">
            <button
              type="submit"
              disabled={!valid || loading}
              className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold transition-all
                bg-gradient-to-r from-emerald-600 to-cyan-600
                hover:from-emerald-500 hover:to-cyan-500
                disabled:opacity-40 disabled:cursor-not-allowed
                text-white shadow-lg shadow-emerald-900/30"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  Estimando...
                </span>
              ) : "Estimar precio"}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mt-5 p-4 rounded-lg border border-red-800/60 bg-red-950/30 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Resultado */}
        {result && (
          <div className="mt-6 rounded-xl border border-emerald-800/50 bg-gradient-to-br from-emerald-950/50 to-gray-900 p-5">
            <p className="text-xs font-semibold uppercase tracking-widest text-emerald-400 mb-3">
              Precio estimado — {result.modelo_usado?.split("_").slice(-1)[0] ?? "hoy"}
            </p>

            {/* Precio principal */}
            <p className="text-4xl font-bold text-white">
              ${result.precio_estimado_ars.toLocaleString("es-AR")}
            </p>
            <p className="text-sm text-gray-500 mt-1">pesos argentinos</p>

            {/* Precio en USD */}
            {precioUSD && (
              <div className="mt-4 flex items-center gap-3">
                <div className="h-px flex-1 bg-gray-800" />
                <div className="text-center">
                  <p className="text-xl font-semibold text-cyan-400">
                    u$s {precioUSD.toLocaleString("es-AR")}
                  </p>
                  <p className="text-xs text-gray-600 mt-0.5">
                    al blue ${result.dolar_blue_venta?.toLocaleString("es-AR")}
                  </p>
                </div>
                <div className="h-px flex-1 bg-gray-800" />
              </div>
            )}

            {/* Advertencia */}
            {result.advertencia && (
              <p className="mt-4 text-xs text-amber-400/80 border-t border-gray-800 pt-3">
                ⚠ {result.advertencia}
              </p>
            )}
          </div>
        )}
      </form>
    </div>
  );
}
