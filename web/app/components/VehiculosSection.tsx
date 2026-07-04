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
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">
          Vehículos en el mercado
        </h2>
        <div className="flex-1 h-px bg-gray-800" />
        <span className="text-xs text-gray-600">{autos.length} publicaciones</span>
      </div>
      <AutosTable autos={autos} marcas={marcas} provincias={provincias} />
    </section>
  );
}
