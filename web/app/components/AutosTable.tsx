"use client";

import { useState, useMemo } from "react";
import type { AutoUsado } from "@/lib/supabase";

type SortKey = "marca" | "modelo" | "precio_ars" | "anio" | "km";
type SortDir = "asc" | "desc";

interface Props {
  autos: AutoUsado[];
  marcas: string[];
  provincias: string[];
}

// Colores claros para los badges de marca — light mode
const BRAND_COLORS: Record<string, string> = {
  Volkswagen: "bg-sky-100 text-sky-700 border-sky-200",
  Toyota:     "bg-red-100 text-red-700 border-red-200",
  Ford:       "bg-blue-100 text-blue-700 border-blue-200",
  Chevrolet:  "bg-amber-100 text-amber-700 border-amber-200",
  Renault:    "bg-yellow-100 text-yellow-800 border-yellow-200",
  Peugeot:    "bg-indigo-100 text-indigo-700 border-indigo-200",
  Fiat:       "bg-orange-100 text-orange-700 border-orange-200",
  Honda:      "bg-rose-100 text-rose-700 border-rose-200",
  Nissan:     "bg-slate-100 text-slate-700 border-slate-200",
  Citroen:    "bg-violet-100 text-violet-700 border-violet-200",
};
const DEFAULT_BADGE = "bg-slate-100 text-slate-600 border-slate-200";

function fmt(n: number) {
  return new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 }).format(n);
}
function fmtKm(n: number) {
  return new Intl.NumberFormat("es-AR").format(n) + " km";
}

const selectCls =
  "bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-700 " +
  "focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/30 " +
  "disabled:opacity-40 transition-colors min-w-0";

const COLS: { key: SortKey; label: string; align: "left" | "right" }[] = [
  { key: "marca",      label: "Marca",   align: "left"  },
  { key: "modelo",     label: "Modelo",  align: "left"  },
  { key: "anio",       label: "Año",     align: "left"  },
  { key: "precio_ars", label: "Precio",  align: "right" },
  { key: "km",         label: "Km",      align: "right" },
];

export default function AutosTable({ autos, marcas, provincias }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("precio_ars");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const [search,    setSearch]    = useState("");
  const [marca,     setMarca]     = useState("");
  const [provincia, setProvincia] = useState("");
  const [anioMin,   setAnioMin]   = useState("");
  const [anioMax,   setAnioMax]   = useState("");
  const [precioMax, setPrecioMax] = useState("");

  const filtered = useMemo(() => {
    return autos.filter((a) => {
      if (marca     && a.marca     !== marca)     return false;
      if (provincia && a.provincia !== provincia) return false;
      if (anioMin   && a.anio < parseInt(anioMin)) return false;
      if (anioMax   && a.anio > parseInt(anioMax)) return false;
      if (precioMax && a.precio_ars > parseInt(precioMax)) return false;
      if (search) {
        const q = search.toLowerCase();
        if (!a.modelo.toLowerCase().includes(q) && !a.marca.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [autos, marca, provincia, anioMin, anioMax, precioMax, search]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const va = a[sortKey] ?? 0;
      const vb = b[sortKey] ?? 0;
      const cmp = typeof va === "string" ? va.localeCompare(vb as string, "es") : (va as number) - (vb as number);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const maxPrecio = useMemo(() => Math.max(...autos.map((a) => a.precio_ars), 1), [autos]);
  const hasFilters = marca || provincia || anioMin || anioMax || precioMax || search;

  function handleSort(key: SortKey) {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  }

  function resetFilters() {
    setSearch(""); setMarca(""); setProvincia("");
    setAnioMin(""); setAnioMax(""); setPrecioMax("");
  }

  return (
    <div className="space-y-4">
      {/* ── Filtros ── */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap gap-3 items-end">

          <div className="flex-1 min-w-[160px]">
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1.5">Buscar</label>
            <input
              type="text"
              placeholder="Marca o modelo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={selectCls + " w-full"}
            />
          </div>

          <div className="min-w-[130px]">
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1.5">Marca</label>
            <select className={selectCls} value={marca} onChange={(e) => setMarca(e.target.value)}>
              <option value="">Todas</option>
              {marcas.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          <div className="min-w-[130px]">
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1.5">Provincia</label>
            <select className={selectCls} value={provincia} onChange={(e) => setProvincia(e.target.value)}>
              <option value="">Todas</option>
              {provincias.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1.5">Año desde</label>
            <input type="number" placeholder="2010" min={1990} max={2026}
              value={anioMin} onChange={(e) => setAnioMin(e.target.value)}
              className={selectCls + " w-24"} />
          </div>
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1.5">Año hasta</label>
            <input type="number" placeholder="2026" min={1990} max={2026}
              value={anioMax} onChange={(e) => setAnioMax(e.target.value)}
              className={selectCls + " w-24"} />
          </div>

          <div className="min-w-[140px]">
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1.5">Precio máx.</label>
            <input type="number" placeholder="Ej: 30000000"
              value={precioMax} onChange={(e) => setPrecioMax(e.target.value)}
              className={selectCls + " w-full"} />
          </div>

          <div className="flex items-end gap-2 ml-auto">
            <span className="text-xs text-slate-400 pb-2.5 whitespace-nowrap">
              {sorted.length} / {autos.length}
            </span>
            {hasFilters && (
              <button
                onClick={resetFilters}
                className="px-3 py-2 rounded-lg text-xs font-medium text-brand-600 border border-brand-200 hover:bg-brand-50 transition-colors"
              >
                Limpiar
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Tabla ── */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-brand-500">
            <tr>
              {COLS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className={`px-4 py-3.5 cursor-pointer select-none text-xs font-semibold uppercase tracking-wider transition-colors text-${col.align}
                    ${sortKey === col.key ? "text-white" : "text-brand-200 hover:text-white"}`}
                >
                  {col.label}
                  {col.key === sortKey
                    ? <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>
                    : <span className="ml-1 opacity-40">↕</span>}
                </th>
              ))}
              <th className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-brand-200">Provincia</th>
              <th className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-brand-200">Relativo</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-slate-400 text-sm">
                  Sin resultados para los filtros seleccionados.
                </td>
              </tr>
            ) : (
              sorted.map((a, i) => (
                <tr
                  key={a.cod}
                  className={`border-b border-slate-100 hover:bg-brand-50/50 transition-colors ${
                    i % 2 === 0 ? "bg-white" : "bg-slate-50/50"
                  }`}
                >
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-medium border ${BRAND_COLORS[a.marca] ?? DEFAULT_BADGE}`}>
                      {a.marca}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={a.url} target="_blank" rel="noopener noreferrer"
                      className="text-slate-800 hover:text-brand-500 transition-colors font-medium"
                    >
                      {a.modelo}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-slate-500 tabular-nums">{a.anio}</td>
                  <td className="px-4 py-3 text-right font-mono font-semibold text-slate-900 tabular-nums">
                    {fmt(a.precio_ars)}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-500 tabular-nums">
                    {a.km <= 1 ? "—" : fmtKm(a.km)}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{a.provincia}</td>
                  <td className="px-4 py-3 w-28">
                    <div className="h-1.5 rounded-full bg-slate-200">
                      <div
                        className="h-1.5 rounded-full bg-brand-500 transition-all"
                        style={{ width: `${(a.precio_ars / maxPrecio) * 100}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
