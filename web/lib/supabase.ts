import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseKey);

export type CotizacionDolar = {
  fecha: string;
  casa: string;
  nombre: string;
  compra: number;
  venta: number;
};

export type AutoUsado = {
  cod: string;
  marca: string;
  modelo: string;
  provincia: string;
  precio_ars: number;
  anio: number;
  km: number;
  url: string;
};
