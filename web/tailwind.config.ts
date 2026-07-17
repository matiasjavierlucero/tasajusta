import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: 'class',
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        // Azul de marca — mismo #2974b4 del ícono
        brand: {
          50:  "#EEF5FB",
          100: "#D5E8F5",
          200: "#A9D0EB",
          300: "#6AADD9",
          400: "#3D8EC8",
          500: "#2974b4",
          600: "#1E5A8C",
          700: "#164571",
          800: "#0F2E4E",
          900: "#081C30",
          950: "#040E1A",
        },
        // Verde de marca — mismo #4caf50 del ícono
        sage: {
          50:  "#F0FDF4",
          100: "#DCFCE7",
          200: "#BBF7D0",
          400: "#4ADE80",
          500: "#4caf50",
          600: "#3A9440",
          700: "#276B2D",
        },
      },
    },
  },
  plugins: [],
};
export default config;
