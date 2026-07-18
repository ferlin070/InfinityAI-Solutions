/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0A0C10",
        surface: "#12151B",
        "surface-raised": "#181C24",
        border: "rgba(255,255,255,0.08)",
        "border-strong": "rgba(255,255,255,0.14)",
        card: "rgba(18, 25, 45, 0.55)",
        "card-border": "rgba(255, 255, 255, 0.08)",
        primary: {
          DEFAULT: "#6C63FF",
          hover: "#5A52E0",
          subtle: "rgba(108,99,255,0.12)",
        },
        accent: {
          gold: "#C9A961",
          success: "#3DD68C",
          danger: "#F0616D",
          green: "#10b981",
          teal: "#06b6d4",
          purple: "#d946ef",
          red: "#ef4444",
        },
        text: {
          DEFAULT: "#E8E9EC",
          muted: "#9BA1AC",
          faint: "#7A8090",
          dark: "#4b5563",
        }
      },
      fontFamily: {
        sans: ['Geist', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}
