import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: "#0a1410",
          card: "#0f1f1a",
          cardHover: "#13261f",
          border: "#1f3a32",
          orange: "#f97316",
          orangeHover: "#ea6a0a",
          emerald: "#10b981",
          emeraldHover: "#0ea372",
          textPrimary: "#ffffff",
          textSecondary: "#9ca3af",
          textMuted: "#6b7280",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter-tight)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
