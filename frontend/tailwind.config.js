/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand system, matched to the AuraDesk mark: warm gold on ink black / off-white.
        aura: {
          gold: {
            50: "#FBF6EC",
            100: "#F5E9CE",
            300: "#E4C588",
            500: "#C9A24B", // primary gold
            600: "#AD8635",
            700: "#8C6A28",
          },
          ink: {
            50: "#F7F7F8",
            100: "#EDEDEF",
            400: "#6B6B72",
            700: "#232327",
            900: "#0E0E10", // near-black, matches wordmark
          },
        },
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
      boxShadow: {
        soft: "0 2px 16px -4px rgb(14 14 16 / 0.08)",
        glass: "0 8px 32px -8px rgb(14 14 16 / 0.18)",
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
