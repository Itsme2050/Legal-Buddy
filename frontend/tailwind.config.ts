import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#eef2f9",
          100: "#d9e2f1",
          200: "#b3c5e3",
          300: "#8aa4d2",
          400: "#5f80bd",
          500: "#3f5fa3",
          600: "#2e4680",
          700: "#253a68",
          800: "#1b2c4e",
          900: "#131f36",
          950: "#0b1424",
        },
        teal: {
          50: "#eefcfa",
          100: "#d3f5f1",
          200: "#abeae4",
          300: "#77dad2",
          400: "#40c4bc",
          500: "#1ba9a3",
          600: "#0f8884",
          700: "#106c6a",
          800: "#125656",
          900: "#134849",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        serif: ["ui-serif", "Georgia", "Cambria", "serif"],
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 240ms ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;