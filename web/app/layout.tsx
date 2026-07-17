import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import AgentChat from "@/app/components/AgentChat";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "TasaJusta — Inteligencia de precios para autos usados",
  description:
    "Estimá el valor real de tu vehículo usado en Argentina. Datos de mercado reales, cruzados con el dólar blue y actualizados semanalmente.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        {/* Evita flash de tema incorrecto al cargar */}
        <script dangerouslySetInnerHTML={{ __html: `
          (function() {
            var t = localStorage.getItem('theme');
            if (t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
              document.documentElement.classList.add('dark');
            }
          })();
        `}} />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
        <AgentChat />
      </body>
    </html>
  );
}
