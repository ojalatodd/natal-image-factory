/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        surface: "#1e293b",
        card: "#334155",
        accent: "#3b82f6",
        accent2: "#8b5cf6",
      },
    },
  },
  plugins: [],
};
