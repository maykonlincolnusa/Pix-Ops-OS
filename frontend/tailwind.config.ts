import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      fontFamily: {
        sans: ["Aptos", "Manrope", "Segoe UI", "sans-serif"],
        display: ["Bahnschrift", "Space Grotesk", "Trebuchet MS", "sans-serif"],
      },
      boxShadow: {
        glow: "0 12px 40px rgba(16, 34, 67, 0.2)",
      },
      backgroundImage: {
        aurora:
          "radial-gradient(circle at 15% 20%, rgba(17, 111, 203, 0.25), transparent 40%), radial-gradient(circle at 85% 5%, rgba(31, 180, 120, 0.22), transparent 36%), radial-gradient(circle at 80% 70%, rgba(32, 44, 96, 0.35), transparent 32%)",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        fadeUp: "fadeUp 0.45s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
