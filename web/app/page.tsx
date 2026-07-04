import { supabase, type CotizacionDolar, type AutoUsado } from "@/lib/supabase";
import AutosTable from "@/app/components/AutosTable";
import PredictForm from "@/app/components/PredictForm";

async function getDolar(): Promise<CotizacionDolar[]> {
  const { data } = await supabase
    .from("cotizaciones_dolar")
    .select("fecha, casa, nombre, compra, venta")
    .order("venta", { ascending: false });
  return data ?? [];
}

async function getAutos(): Promise<AutoUsado[]> {
  const { data } = await supabase
    .from("autos_usados")
    .select("cod, marca, modelo, provincia, precio_ars, anio, km, url");
  return data ?? [];
}

const FEATURED = ["blue", "oficial"];

export default async function HomePage() {
  const [dolar, autos] = await Promise.all([getDolar(), getAutos()]);

  const featured = dolar.filter((c) => FEATURED.includes(c.casa));
  const rest = dolar.filter((c) => !FEATURED.includes(c.casa));

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">

      {/* Header */}
      <header className="relative overflow-hidden border-b border-gray-800">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-950 via-gray-950 to-cyan-950 opacity-80" />
        <div className="relative px-8 py-12">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-2 h-8 rounded-full bg-gradient-to-b from-emerald-400 to-cyan-400" />
            <h1 className="text-4xl font-bold tracking-tight">TasaJusta</h1>
          </div>
          <p className="text-gray-400 text-lg ml-5">
            Inteligencia de precios de autos usados en Argentina
          </p>
          <div className="flex gap-6 mt-6 ml-5 text-sm text-gray-500">
            <span>
              <span className="text-emerald-400 font-semibold">{autos.length}</span> listings
            </span>
            <span>
              <span className="text-emerald-400 font-semibold">
                {[...new Set(autos.map((a) => a.marca))].length}
              </span> marcas
            </span>
            <span>Actualizado hoy</span>
          </div>
        </div>
      </header>

      <main className="px-8 py-10 max-w-7xl mx-auto">

        {/* Cotizador */}
        <section className="mb-12">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-5">
            Cotizador
          </h2>
          <PredictForm />
        </section>

        {/* Cotizaciones del dólar */}
        <section className="mb-12">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-5">
            Cotizaciones del dólar
          </h2>

          {/* Blue + Oficial destacados */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            {featured.map((c) => (
              <div
                key={c.casa}
                className="relative overflow-hidden rounded-xl p-5 border border-emerald-900/50 bg-gradient-to-br from-emerald-950/60 to-gray-900"
              >
                <p className="text-xs font-semibold uppercase tracking-widest text-emerald-400 mb-3">
                  {c.nombre}
                </p>
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-3xl font-bold text-white">
                      ${c.venta.toLocaleString("es-AR")}
                    </p>
                    <p className="text-sm text-gray-400 mt-1">venta</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-semibold text-gray-300">
                      ${c.compra.toLocaleString("es-AR")}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">compra</p>
                  </div>
                </div>
                {/* spread bar */}
                <div className="mt-4 h-1 rounded-full bg-gray-800">
                  <div
                    className="h-1 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                    style={{ width: `${(c.compra / c.venta) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  spread ${(c.venta - c.compra).toLocaleString("es-AR")}
                </p>
              </div>
            ))}
          </div>

          {/* Resto de cotizaciones */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {rest.map((c) => (
              <div
                key={c.casa}
                className="rounded-lg p-4 border border-gray-800 bg-gray-900/50"
              >
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                  {c.nombre}
                </p>
                <p className="text-lg font-bold">${c.venta.toLocaleString("es-AR")}</p>
                <p className="text-xs text-gray-600 mt-1">
                  compra ${c.compra.toLocaleString("es-AR")}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Autos usados */}
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-5">
            Autos usados
          </h2>
          <AutosTable autos={autos} />
        </section>
      </main>
    </div>
  );
}
