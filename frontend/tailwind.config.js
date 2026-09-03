/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        asphalt: "#14161A",
        panel: "#1B1E24",
        hairline: "#2A2E36",
        ink: "#ECEEF1",
        muted: "#8B92A0",
        amber: "#F2B705",
        danger: "#E5484D",
        okgreen: "#3DDC84",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
