import { supabase, type AutoUsado } from "@/lib/supabase";
import AutosTable from "./AutosTable";

async function getAutos(): Promise<AutoUsado[]> {
  const { data } = await supabase
    .from("autos_usados")
    .select("cod, marca, modelo, provincia, precio_ars, anio, km, url")
    .order("scraped_at", { ascending: false })
    .limit(1000);
  return data ?? [];
}

export default async function VehiculosSection() {
  const autos = await getAutos();

  const marcas    = [...new Set(autos.map((a) => a.marca))].sort();
  const provincias = [...new Set(autos.map((a) => a.provincia))].sort();

  return (
    <section>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Vehículos en el mercado</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Publicaciones de DeRuedas y Kavak</p>
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-full">
          {autos.length} publicaciones
        </span>
      </div>
      <AutosTable autos={autos} marcas={marcas} provincias={provincias} />
    </section>
  );
}
