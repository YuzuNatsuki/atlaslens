/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0f766e",
          dark: "#0d544e",
          light: "#5eead4",
          50: "#f0fdfa",
          100: "#ccfbf1",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Hiragino Sans",
          "Noto Sans JP",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(15, 23, 42, 0.04), 0 1px 3px 0 rgba(15, 23, 42, 0.06)",
        pop: "0 6px 24px -6px rgba(13, 84, 78, 0.18)",
        elevated:
          "0 1px 2px rgba(15, 23, 42, 0.04), 0 12px 32px -12px rgba(13, 84, 78, 0.18)",
        focus: "0 0 0 4px rgba(20, 184, 166, 0.18)",
      },
      backgroundImage: {
        "brand-gradient":
          "linear-gradient(135deg, #0f766e 0%, #14b8a6 40%, #5eead4 100%)",
        "hero-mesh":
          "radial-gradient(at 0% 0%, rgba(94, 234, 212, 0.35) 0px, transparent 50%), radial-gradient(at 100% 0%, rgba(15, 118, 110, 0.32) 0px, transparent 50%), radial-gradient(at 50% 100%, rgba(20, 184, 166, 0.22) 0px, transparent 60%)",
        "panel-soft":
          "linear-gradient(180deg, rgba(15, 118, 110, 0.04) 0%, rgba(15, 118, 110, 0) 100%)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(2px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out",
        "slide-up": "slide-up 320ms cubic-bezier(0.22, 1, 0.36, 1)",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
