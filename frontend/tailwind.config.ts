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
          DEFAULT: "#061A1A",
          soft: "#0A2323",
          card: "#0F2B2B",
          elev: "#123333",
        },
        border: {
          DEFAULT: "#214242",
          soft: "#2A5656",
        },
        brand: {
          orange: "#EE7F2D",
          orangeHover: "#FF9448",
          mint: "#5FD0B8",
          cyan: "#79E0C4",
        },
        text: {
          DEFAULT: "#E7F3F0",
          muted: "#9FC2BA",
          dim: "#6D938A",
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
          "radial-gradient(1100px 560px at 18% -5%, rgba(238,127,45,0.14), transparent 62%), radial-gradient(920px 520px at 88% 8%, rgba(95,208,184,0.11), transparent 64%)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
export default config
