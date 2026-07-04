import { supabase, type CotizacionDolar } from "@/lib/supabase";

async function getDolar(): Promise<CotizacionDolar[]> {
  const { data } = await supabase
    .from("cotizaciones_dolar")
    .select("fecha, casa, nombre, compra, venta")
    .order("venta", { ascending: false });
  return data ?? [];
}

const FEATURED = ["blue", "oficial"];

function fmt(n: number) {
  return new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 }).format(n);
}

export default async function DolarSection() {
  const cotizaciones = await getDolar();
  const featured = cotizaciones.filter((c) => FEATURED.includes(c.casa));
  const rest = cotizaciones.filter((c) => !FEATURED.includes(c.casa));

  if (!cotizaciones.length) return null;

  return (
    <section className="mb-10">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">
          Cotizaciones del dólar
        </h2>
        <div className="flex-1 h-px bg-gray-800" />
        <span className="text-xs text-gray-600">{cotizaciones[0]?.fecha}</span>
      </div>

      <div className="flex flex-wrap gap-3">
        {/* Blue y Oficial — chips destacados */}
        {featured.map((c) => (
          <div
            key={c.casa}
            className="flex items-center gap-4 rounded-lg px-4 py-3 border border-emerald-900/60 bg-emerald-950/30"
          >
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-400 mb-0.5">
                {c.nombre}
              </p>
              <p className="text-xl font-bold text-white leading-none">
                ${fmt(c.venta)}
              </p>
            </div>
            <div className="text-right border-l border-emerald-900/50 pl-4">
              <p className="text-[10px] text-gray-500 mb-0.5">compra</p>
              <p className="text-sm font-semibold text-gray-300">${fmt(c.compra)}</p>
            </div>
          </div>
        ))}

        {/* Resto — pills compactos */}
        {rest.map((c) => (
          <div
            key={c.casa}
            className="flex items-center gap-2 rounded-lg px-3 py-2.5 border border-gray-800 bg-gray-900/40"
          >
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wide">{c.nombre}</p>
              <p className="text-sm font-bold text-gray-200">${fmt(c.venta)}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
