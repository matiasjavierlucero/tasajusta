"use client";

import { useState } from "react";
import type { AutoUsado } from "@/lib/supabase";

type SortKey = "marca" | "modelo" | "precio_ars" | "anio";
type SortDir = "asc" | "desc";

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
  { key: "marca",     label: "Marca",     align: "left"  },
  { key: "modelo",    label: "Modelo",    align: "left"  },
  { key: "anio",      label: "Año",       align: "left"  },
  { key: "precio_ars",label: "Precio ARS",align: "right" },
];

export default function AutosTable({ autos }: { autos: AutoUsado[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("precio_ars");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

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
    const cmp = typeof va === "string"
      ? va.localeCompare(vb as string, "es")
      : (va as number) - (vb as number);
    return sortDir === "asc" ? cmp : -cmp;
  });

  function SortIcon({ col }: { col: SortKey }) {
    if (col !== sortKey) return <span className="ml-1 opacity-20">↕</span>;
    return <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead className="bg-gray-900 text-gray-400 uppercase text-xs">
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className={`px-4 py-3 cursor-pointer select-none hover:text-gray-200 transition-colors text-${col.align}`}
              >
                {col.label}
                <SortIcon col={col.key} />
              </th>
            ))}
            <th className="px-4 py-3 text-left">Km</th>
            <th className="px-4 py-3 text-left">Provincia</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {sorted.map((a) => (
            <tr key={a.cod} className="hover:bg-gray-900 transition-colors">
              <td className="px-4 py-3 font-medium text-gray-100">{a.marca}</td>
              <td className="px-4 py-3">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 hover:underline"
                >
                  {a.modelo}
                </a>
              </td>
              <td className="px-4 py-3 text-gray-300">{a.anio}</td>
              <td className="px-4 py-3 text-right font-mono font-semibold">
                {formatPeso(a.precio_ars)}
              </td>
              <td className="px-4 py-3 text-gray-300">
                {a.km <= 1 ? "—" : formatKm(a.km)}
              </td>
              <td className="px-4 py-3 text-gray-400">{a.provincia}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
