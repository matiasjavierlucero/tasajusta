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
    <section>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Oportunidades del mercado</h2>
          <p className="text-sm text-slate-500 mt-0.5">Publicaciones más de 10% por debajo del precio estimado</p>
        </div>
        <span className="text-xs font-semibold text-sage-700 bg-sage-50 border border-sage-200 px-2.5 py-1 rounded-full">
          {oportunidades.length} encontradas
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {oportunidades.map((auto) => {
          const ahorro = auto.precio_estimado - auto.precio_ars;
          const pct    = Math.round(auto.oportunidad_score * 100);

          return (
            <a
              key={auto.cod}
              href={`https://www.deruedas.com.ar${auto.url}`}
              target="_blank"
              rel="noopener noreferrer"
              className="group block rounded-xl border border-slate-200 bg-white
                         hover:shadow-md hover:border-brand-300 transition-all p-5"
            >
              {/* Encabezado */}
              <div className="flex items-start justify-between gap-2 mb-4">
                <div>
                  <p className="font-semibold text-slate-900">
                    {auto.marca} {auto.modelo}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {auto.anio} · {auto.provincia}
                  </p>
                </div>
                {/* Badge verde = oportunidad de compra, alineado con ícono */}
                <span className="shrink-0 text-xs font-bold px-2.5 py-1 rounded-full bg-sage-500 text-white">
                  −{pct}%
                </span>
              </div>

              {/* Comparación de precios */}
              <div className="flex items-end justify-between border-t border-slate-100 pt-4">
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Publicado</p>
                  <p className="text-lg font-bold text-slate-900">${fmt(auto.precio_ars)}</p>
                </div>
                <div className="text-slate-300 pb-1 text-lg">→</div>
                <div className="text-right">
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Estimado</p>
                  <p className="text-lg font-bold text-sage-600">${fmt(auto.precio_estimado)}</p>
                </div>
              </div>

              <p className="text-xs text-slate-500 mt-3 pt-2 border-t border-slate-100">
                Ahorro estimado: <span className="font-semibold text-sage-600">${fmt(ahorro)}</span>
              </p>
            </a>
          );
        })}
      </div>
    </section>
  );
}
