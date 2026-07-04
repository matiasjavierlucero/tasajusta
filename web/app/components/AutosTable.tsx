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

const BRAND_COLORS: Record<string, string> = {
  Volkswagen: "bg-sky-900/60 text-sky-300 border-sky-800",
  Toyota:     "bg-red-900/60 text-red-300 border-red-800",
  Ford:       "bg-blue-900/60 text-blue-300 border-blue-800",
  Chevrolet:  "bg-amber-900/60 text-amber-300 border-amber-800",
  Renault:    "bg-yellow-900/60 text-yellow-300 border-yellow-800",
  Peugeot:    "bg-indigo-900/60 text-indigo-300 border-indigo-800",
  Fiat:       "bg-orange-900/60 text-orange-300 border-orange-800",
  Honda:      "bg-rose-900/60 text-rose-300 border-rose-800",
  Nissan:     "bg-slate-700/80 text-slate-200 border-slate-600",
  Citroen:    "bg-violet-900/60 text-violet-300 border-violet-800",
};
const DEFAULT_BADGE = "bg-gray-800 text-gray-300 border-gray-700";

function fmt(n: number) {
  return new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 }).format(n);
}
function fmtKm(n: number) {
  return new Intl.NumberFormat("es-AR").format(n) + " km";
}

const selectCls =
  "bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-300 " +
  "focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 " +
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

  // Filtros
  const [search,    setSearch]    = useState("");
  const [marca,     setMarca]     = useState("");
  const [provincia, setProvincia] = useState("");
  const [anioMin,   setAnioMin]   = useState("");
  const [anioMax,   setAnioMax]   = useState("");
  const [precioMax, setPrecioMax] = useState("");

  const filtered = useMemo(() => {
    return autos.filter((a) => {
      if (marca     && a.marca    !== marca)     return false;
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
      {/* ── Barra de filtros ── */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
        <div className="flex flex-wrap gap-3 items-end">

          {/* Búsqueda libre */}
          <div className="flex-1 min-w-[160px]">
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-gray-600 mb-1.5">
              Buscar
            </label>
            <input
              type="text"
              placeholder="Marca o modelo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={selectCls + " w-full"}
            />
          </div>

          {/* Marca */}
          <div className="min-w-[130px]">
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-gray-600 mb-1.5">
              Marca
            </label>
            <select className={selectCls} value={marca} onChange={(e) => setMarca(e.target.value)}>
              <option value="">Todas</option>
              {marcas.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          {/* Provincia */}
          <div className="min-w-[130px]">
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-gray-600 mb-1.5">
              Provincia
            </label>
            <select className={selectCls} value={provincia} onChange={(e) => setProvincia(e.target.value)}>
              <option value="">Todas</option>
              {provincias.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {/* Año desde/hasta */}
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-gray-600 mb-1.5">
              Año desde
            </label>
            <input
              type="number" placeholder="2010" min={1990} max={2026}
              value={anioMin} onChange={(e) => setAnioMin(e.target.value)}
              className={selectCls + " w-24"}
            />
          </div>
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-gray-600 mb-1.5">
              Año hasta
            </label>
            <input
              type="number" placeholder="2026" min={1990} max={2026}
              value={anioMax} onChange={(e) => setAnioMax(e.target.value)}
              className={selectCls + " w-24"}
            />
          </div>

          {/* Precio máximo */}
          <div className="min-w-[140px]">
            <label className="block text-[10px] font-semibold uppercase tracking-widest text-gray-600 mb-1.5">
              Precio máx.
            </label>
            <input
              type="number" placeholder="Ej: 30000000"
              value={precioMax} onChange={(e) => setPrecioMax(e.target.value)}
              className={selectCls + " w-full"}
            />
          </div>

          {/* Acciones */}
          <div className="flex items-end gap-2 ml-auto">
            <span className="text-xs text-gray-500 pb-2.5 whitespace-nowrap">
              {sorted.length} / {autos.length}
            </span>
            {hasFilters && (
              <button
                onClick={resetFilters}
                className="px-3 py-2 rounded-lg text-xs text-gray-400 border border-gray-700 hover:border-gray-600 hover:text-gray-200 transition-colors"
              >
                Limpiar
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Tabla ── */}
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-800 bg-gray-900/60">
            <tr>
              {COLS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className={`px-4 py-3 cursor-pointer select-none text-xs font-semibold uppercase tracking-widest transition-colors text-${col.align}
                    ${sortKey === col.key ? "text-emerald-400" : "text-gray-500 hover:text-gray-300"}`}
                >
                  {col.label}
                  {col.key === sortKey
                    ? <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>
                    : <span className="ml-1 opacity-20">↕</span>}
                </th>
              ))}
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-gray-500">
                Provincia
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-gray-500">
                Relativo
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-gray-600 text-sm">
                  Sin resultados para los filtros seleccionados.
                </td>
              </tr>
            ) : (
              sorted.map((a, i) => (
                <tr
                  key={a.cod}
                  className={`border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors ${
                    i % 2 === 0 ? "bg-gray-900/20" : "bg-transparent"
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
                      className="text-gray-100 hover:text-emerald-400 transition-colors font-medium"
                    >
                      {a.modelo}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-gray-400 tabular-nums">{a.anio}</td>
                  <td className="px-4 py-3 text-right font-mono font-semibold text-gray-100 tabular-nums">
                    {fmt(a.precio_ars)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-400 tabular-nums">
                    {a.km <= 1 ? "—" : fmtKm(a.km)}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{a.provincia}</td>
                  <td className="px-4 py-3 w-28">
                    <div className="h-1.5 rounded-full bg-gray-800">
                      <div
                        className="h-1.5 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all"
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
