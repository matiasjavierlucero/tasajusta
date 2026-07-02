import { supabase, type CotizacionDolar, type AutoUsado } from "@/lib/supabase";
import AutosTable from "@/app/components/AutosTable";

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

export default async function HomePage() {
  const [dolar, autos] = await Promise.all([getDolar(), getAutos()]);

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <h1 className="text-3xl font-bold mb-2">TasaJusta</h1>
      <p className="text-gray-400 mb-10">
        Inteligencia de precios de autos usados en Argentina
      </p>

      {/* Cotizaciones del dólar */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4 text-emerald-400">
          Cotizaciones del dólar
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {dolar.map((c) => (
            <div
              key={c.casa}
              className="bg-gray-900 rounded-lg p-4 border border-gray-800"
            >
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                {c.nombre}
              </p>
              <p className="text-lg font-bold text-white">
                ${c.venta.toLocaleString("es-AR")}
              </p>
              <p className="text-xs text-gray-500">
                compra ${c.compra.toLocaleString("es-AR")}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Autos usados */}
      <section>
        <h2 className="text-xl font-semibold mb-4 text-emerald-400">
          Autos usados{" "}
          <span className="text-gray-400 font-normal text-base">
            — {autos.length} listings
          </span>
        </h2>
        <AutosTable autos={autos} />
      </section>
    </main>
  );
}
