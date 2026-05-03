import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./ui/index.html", "./ui/src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#7c3aed",
          600: "#4318ff",
          700: "#3311db",
          800: "#2910b8",
          900: "#1f0d91"
        },
        horizon: {
          background: "#f4f7fe",
          card: "#ffffff",
          nav: "#0f1535",
          text: "#1b2559",
          muted: "#a3aed0",
          border: "#e9edf7",
          success: "#05cd99",
          warning: "#ffb547",
          danger: "#ee5d50",
          info: "#01b8ff"
        }
      },
      boxShadow: {
        horizon: "0 20px 40px rgba(112, 144, 176, 0.12)",
        soft: "0 8px 24px rgba(67, 24, 255, 0.08)"
      },
      borderRadius: {
        "4xl": "2rem"
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
