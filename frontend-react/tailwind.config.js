/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#090d16",
        card: "rgba(17, 25, 40, 0.75)",
        "card-border": "rgba(255, 255, 255, 0.08)",
        primary: {
          DEFAULT: "#8b5cf6",
          hover: "#7c3aed",
        },
        accent: {
          green: "#10b981",
          teal: "#06b6d4",
          purple: "#d946ef",
          red: "#ef4444",
        },
        text: {
          DEFAULT: "#f3f4f6",
          muted: "#9ca3af",
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
