/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,js,jsx}"],
  theme: {
    extend: {
      colors: {
        hero: "#FFA527",
      },
      screens: {
        sm: "480px",
        md: "768px",
        lg: "1024px",
        xl: "1280px",
        "2xl": "1536px",
      },
      fontFamily: {
        itim: ["Itim", "cursive"],
      },
      animation: {
        "spin-slow": "spin 8s linear infinite",
      },
    },
  },
  plugins: [],
};
