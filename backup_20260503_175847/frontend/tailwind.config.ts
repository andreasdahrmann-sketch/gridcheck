import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./pages/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0A1410",
          soft: "#0E1F1A",
          card: "#13201B",
          elev: "#162822",
        },
        border: {
          DEFAULT: "#1F2F28",
          soft: "#243A32",
        },
        brand: {
          orange: "#E67A2E",
          orangeHover: "#F08A3E",
          lime: "#C9D67A",
        },
        text: {
          DEFAULT: "#E8EDE8",
          muted: "#8FA39A",
          dim: "#5F726B",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
      backgroundImage: {
        "hero-radial":
          "radial-gradient(1200px 600px at 20% 0%, rgba(230,122,46,0.10), transparent 60%), radial-gradient(900px 500px at 90% 10%, rgba(201,214,122,0.08), transparent 60%)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
export default config
