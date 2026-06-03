/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 900: "#0c1e3a", 800: "#132a52", 700: "#1e3a5f" },
        road: { 500: "#d97706", 600: "#b45309" },
      },
      fontFamily: {
        display: ["Georgia", "serif"],
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
