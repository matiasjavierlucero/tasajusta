import { supabase } from "@/lib/supabase";

type Oportunidad = {
  cod: string;
  marca: string;
  modelo: string;
  anio: number;
  provincia: string;
  precio_ars: number;
  precio_estimado: number;
  oportunidad_score: number;
  url: string;
};

async function getOportunidades(): Promise<Oportunidad[]> {
  const { data } = await supabase
    .from("autos_usados")
    .select("cod, marca, modelo, anio, provincia, precio_ars, precio_estimado, oportunidad_score, url")
    .gt("oportunidad_score", 0.10)
    .order("oportunidad_score", { ascending: false })
    .limit(20);
  return (data ?? []) as Oportunidad[];
}

function fmt(n: number) {
  return new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 }).format(n);
}

export default async function OportunidadesSection() {
  const oportunidades = await getOportunidades();

  if (!oportunidades.length) return null;

  return (
    <section className="mb-10">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">
          Oportunidades del mercado
        </h2>
        <div className="flex-1 h-px bg-gray-800" />
        <span className="text-xs text-gray-600">
          publicaciones por debajo del precio estimado
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {oportunidades.map((auto) => {
          const ahorro = auto.precio_estimado - auto.precio_ars;
          const pct    = Math.round(auto.oportunidad_score * 100);

          return (
            <a
              key={auto.cod}
              href={`https://www.deruedas.com.ar${auto.url}`}
              target="_blank"
              rel="noopener noreferrer"
              className="group block rounded-xl border border-gray-800 bg-gray-900/40
                         hover:border-emerald-700/60 hover:bg-emerald-950/20 transition-colors p-4"
            >
              {/* Encabezado */}
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <p className="text-sm font-semibold text-white leading-tight">
                    {auto.marca} {auto.modelo}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {auto.anio} · {auto.provincia}
                  </p>
                </div>
                {/* Badge de descuento */}
                <span className="shrink-0 text-xs font-bold px-2 py-1 rounded-full
                                 bg-emerald-900/60 text-emerald-300 border border-emerald-800/60">
                  −{pct}%
                </span>
              </div>

              {/* Precios */}
              <div className="flex items-end gap-3">
                <div>
                  <p className="text-[10px] text-gray-600 mb-0.5">Publicado</p>
                  <p className="text-lg font-bold text-white">${fmt(auto.precio_ars)}</p>
                </div>
                <div className="text-gray-700 pb-0.5">→</div>
                <div>
                  <p className="text-[10px] text-gray-600 mb-0.5">Estimado</p>
                  <p className="text-lg font-semibold text-emerald-400">${fmt(auto.precio_estimado)}</p>
                </div>
              </div>

              {/* Ahorro */}
              <p className="text-xs text-gray-500 mt-2 border-t border-gray-800/60 pt-2">
                ${fmt(ahorro)} por debajo del mercado
              </p>
            </a>
          );
        })}
      </div>
    </section>
  );
}
