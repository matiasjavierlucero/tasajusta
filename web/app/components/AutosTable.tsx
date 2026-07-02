"use client";

import { useState } from "react";
import type { AutoUsado } from "@/lib/supabase";

type SortKey = "marca" | "modelo" | "precio_ars" | "anio";
type SortDir = "asc" | "desc";

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

function formatPeso(n: number) {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(n);
}

function formatKm(n: number) {
  return new Intl.NumberFormat("es-AR").format(n) + " km";
}

const COLUMNS: { key: SortKey; label: string; align: "left" | "right" }[] = [
  { key: "marca",      label: "Marca",      align: "left"  },
  { key: "modelo",     label: "Modelo",     align: "left"  },
  { key: "anio",       label: "Año",        align: "left"  },
  { key: "precio_ars", label: "Precio ARS", align: "right" },
];

export default function AutosTable({ autos }: { autos: AutoUsado[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("precio_ars");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const maxPrecio = Math.max(...autos.map((a) => a.precio_ars));

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sorted = [...autos].sort((a, b) => {
    const va = a[sortKey];
    const vb = b[sortKey];
    const cmp =
      typeof va === "string"
        ? va.localeCompare(vb as string, "es")
        : (va as number) - (vb as number);
    return sortDir === "asc" ? cmp : -cmp;
  });

  function SortIcon({ col }: { col: SortKey }) {
    if (col !== sortKey) return <span className="ml-1 opacity-20">↕</span>;
    return (
      <span className="ml-1 text-emerald-400">{sortDir === "asc" ? "↑" : "↓"}</span>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800">
      <table className="w-full text-sm">
        <thead className="border-b border-gray-800">
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className={`px-4 py-3 cursor-pointer select-none text-xs font-semibold uppercase tracking-widest text-gray-500 hover:text-gray-300 transition-colors text-${col.align} ${sortKey === col.key ? "text-gray-300" : ""}`}
              >
                {col.label}
                <SortIcon col={col.key} />
              </th>
            ))}
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-gray-500">
              Km
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-gray-500">
              Provincia
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-gray-500">
              Precio relativo
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((a, i) => (
            <tr
              key={a.cod}
              className={`border-b border-gray-800/50 hover:bg-gray-900/80 transition-colors ${
                i % 2 === 0 ? "bg-gray-900/20" : "bg-transparent"
              }`}
            >
              <td className="px-4 py-3">
                <span
                  className={`inline-block px-2 py-0.5 rounded-md text-xs font-medium border ${
                    BRAND_COLORS[a.marca] ?? DEFAULT_BADGE
                  }`}
                >
                  {a.marca}
                </span>
              </td>
              <td className="px-4 py-3">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-100 hover:text-emerald-400 transition-colors font-medium"
                >
                  {a.modelo}
                </a>
              </td>
              <td className="px-4 py-3 text-gray-400">{a.anio}</td>
              <td className="px-4 py-3 text-right font-mono font-semibold text-gray-100">
                {formatPeso(a.precio_ars)}
              </td>
              <td className="px-4 py-3 text-gray-400">
                {a.km <= 1 ? "—" : formatKm(a.km)}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">{a.provincia}</td>
              <td className="px-4 py-3 w-32">
                <div className="h-1.5 rounded-full bg-gray-800">
                  <div
                    className="h-1.5 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                    style={{ width: `${(a.precio_ars / maxPrecio) * 100}%` }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
