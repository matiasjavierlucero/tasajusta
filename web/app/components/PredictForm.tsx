"use client";

import { useState } from "react";

// Marcas y modelos conocidos por el modelo ML (los que vio en training)
// Capitalization debe coincidir exactamente con los valores en Supabase/gold
const MODELOS_POR_MARCA: Record<string, string[]> = {
  "Alfa Romeo":   ["Mito"],
  Audi:           ["A1"],
  Baic:           ["D20", "Eu5"],
  Bmw:            ["Serie 2"],
  Chery:          ["QQ", "Tiggo", "Tiggo 2", "Tiggo 2 Pro", "Tiggo 5", "Tiggo 7 Pro"],
  Chevrolet:      ["Agile", "Aveo", "Captiva", "Celta", "Classic", "Cobalt", "Cruze", "Cruze II", "Equinox", "Joy", "Meriva", "Montana", "Onix", "Onix +", "Prisma", "Spin", "Tracker", "Trailblazer"],
  Citroen:        ["Basalt", "Berlingo", "C-Elysée", "C3", "C3 Aircross", "C3 Picasso", "C4", "C4 Cactus", "C4 Grand Picaso", "C4 Lounge"],
  Dodge:          ["Journey"],
  Ds:             ["Ds 3"],
  Fiat:           ["500", "500X", "600", "Argo", "Cronos", "Fastback", "Grand Siena", "Idea", "Mobi", "Nuevo Palio", "Palio", "Pulse", "Punto", "Siena", "Strada", "Titano", "Toro"],
  Ford:           ["Bronco Sport", "EcoSport", "Fiesta", "Fiesta KD", "Fiesta Kinetic Design", "Focus", "Focus III", "Ka", "Kuga", "Maverick", "Mondeo", "Ranger", "Territory"],
  Honda:          ["City", "Civic", "CRV", "Fit", "HR V", "HR-V"],
  Hyundai:        ["Creta", "Grand i10", "HB20", "I10", "Tucson"],
  Jeep:           ["Cherokee", "Commander", "Compass", "Renegade"],
  Kia:            ["Picanto", "Rio", "Sportage"],
  "Mercedes Benz":["Clase C", "Clase GLA", "Sprinter", "Vito"],
  Mitsubishi:     ["Lancer"],
  Nissan:         ["Frontier", "Kicks", "March", "Note", "Sentra", "Tiida", "Versa"],
  Peugeot:        ["2008", "206", "207", "208", "3008", "301", "307", "308", "408", "5008", "Partner"],
  RAM:            ["1500", "Dakota", "Rampage"],
  Renault:        ["Alaskan", "Captur", "Clio", "Duster", "Duster Oroch", "Fluence", "Kangoo", "Kardian", "Kwid", "Logan", "Sandero", "Sandero Stepway", "Symbol"],
  Smart:          ["Forfour"],
  Toyota:         ["C-Hr", "Corolla", "Corolla Cross", "Etios", "Hilux", "Hilux SW4", "Innova", "RAV4", "SW4", "Yaris"],
  Volkswagen:     ["Amarok", "Bora", "Fox", "Gol", "Gol Trend", "Golf", "Nivus", "Passat", "Polo", "Saveiro", "Suran", "Suran Cross", "T-Cross", "Taos", "Tera", "Tiguan", "Tiguan Allspace", "up", "Vento", "Virtus", "Voyage"],
};

const PROVINCIAS = [
  "Buenos Aires",
  "Buenos Aires Ciudad",
  "Catamarca",
  "Chaco",
  "Chubut",
  "Cordoba",
  "Corrientes",
  "Entre Rios",
  "Formosa",
  "Jujuy",
  "La Pampa",
  "La Rioja",
  "Mendoza",
  "Misiones",
  "Neuquen",
  "Rio Negro",
  "Salta",
  "San Juan",
  "San Luis",
  "Santa Cruz",
  "Santa Fe",
  "Santiago del Estero",
  "Tierra del Fuego",
  "Tucuman",
];
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
  "w-full bg-white border border-slate-300 rounded-lg px-3 py-2.5 text-sm text-slate-900 " +
  "focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 " +
  "disabled:opacity-40 disabled:cursor-not-allowed transition-colors";

const labelCls = "block text-xs font-semibold text-slate-600 mb-1.5";

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
    <div>
      {/* Título del formulario */}
      <div className="px-6 py-5 border-b border-slate-200 bg-brand-500">
        <h3 className="text-base font-semibold text-white">Cotizá tu auto</h3>
        <p className="text-sm text-brand-100 mt-0.5">
          Estimación basada en publicaciones reales del mercado.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">

          {/* Marca */}
          <div>
            <label className={labelCls}>Marca</label>
            <select className={selectCls} value={marca} onChange={e => handleMarca(e.target.value)}>
              <option value="">Seleccioná una</option>
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
              <option value="">Seleccioná una</option>
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
                bg-brand-500 hover:bg-brand-600 active:bg-brand-700
                disabled:opacity-40 disabled:cursor-not-allowed
                text-white shadow-sm"
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
          <div className="mt-5 p-4 rounded-lg border border-red-200 bg-red-50 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Resultado */}
        {result && (
          <div className="mt-6 rounded-xl border border-brand-200 bg-brand-50 p-5">
            <p className="text-xs font-semibold text-brand-600 uppercase tracking-wide mb-3">
              Precio estimado — {result.modelo_usado?.split("_").slice(-1)[0] ?? "hoy"}
            </p>

            {/* Precio principal */}
            <p className="text-4xl font-bold text-slate-900">
              ${result.precio_estimado_ars.toLocaleString("es-AR")}
            </p>
            <p className="text-sm text-slate-500 mt-1">pesos argentinos</p>

            {/* Precio en USD */}
            {precioUSD && (
              <div className="mt-4 flex items-center gap-3">
                <div className="h-px flex-1 bg-brand-200" />
                <div className="text-center">
                  <p className="text-xl font-semibold text-brand-600">
                    u$s {precioUSD.toLocaleString("es-AR")}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    al blue ${result.dolar_blue_venta?.toLocaleString("es-AR")}
                  </p>
                </div>
                <div className="h-px flex-1 bg-brand-200" />
              </div>
            )}

            {/* Advertencia */}
            {result.advertencia && (
              <p className="mt-4 text-xs text-amber-700 border-t border-brand-200 pt-3">
                ⚠ {result.advertencia}
              </p>
            )}
          </div>
        )}
      </form>
    </div>
  );
}
