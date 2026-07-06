import { supabase, type CotizacionDolar } from "@/lib/supabase";

async function getDolar(): Promise<CotizacionDolar[]> {
  const { data: latest } = await supabase
    .from("cotizaciones_dolar")
    .select("fecha")
    .order("fecha", { ascending: false })
    .limit(1)
    .single();

  if (!latest) return [];

  const { data } = await supabase
    .from("cotizaciones_dolar")
    .select("fecha, casa, nombre, compra, venta")
    .eq("fecha", latest.fecha)
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
    <section>
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-bold text-slate-900">Cotizaciones del dólar</h2>
        <span className="text-xs text-slate-400 bg-slate-100 px-2.5 py-1 rounded-full">
          {cotizaciones[0]?.fecha}
        </span>
      </div>

      <div className="flex flex-wrap gap-3">
        {/* Blue y Oficial — tarjetas destacadas */}
        {featured.map((c) => (
          <div
            key={c.casa}
            className="flex items-center gap-5 rounded-xl px-5 py-4 border-2 border-brand-500 bg-brand-50 min-w-[170px]"
          >
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-brand-500 mb-1">
                {c.nombre}
              </p>
              <p className="text-2xl font-bold text-slate-900 leading-none">
                ${fmt(c.venta)}
              </p>
            </div>
            <div className="text-right border-l border-brand-200 pl-4">
              <p className="text-[10px] text-slate-400 mb-1">compra</p>
              <p className="text-sm font-semibold text-slate-600">${fmt(c.compra)}</p>
            </div>
          </div>
        ))}

        {/* Resto — pills */}
        {rest.map((c) => (
          <div
            key={c.casa}
            className="flex items-center gap-2 rounded-xl px-4 py-3 border border-slate-200 bg-white min-w-[120px]"
          >
            <div>
              <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-0.5">{c.nombre}</p>
              <p className="text-base font-bold text-slate-800">${fmt(c.venta)}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
