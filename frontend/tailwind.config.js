/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Light theme - "ANPR Console" bright identity.
        canvas: "#F3F5FA",     // page background
        surface: "#FFFFFF",    // cards, sidebar, topbar
        sunken: "#F7F8FC",     // table header rows, inset panels
        border: "#E6E9F2",
        ink: "#171A29",        // primary text
        subtle: "#6B7186",     // secondary text
        faint: "#9AA0B4",      // placeholders, disabled

        primary: "#3654F4",    // main blue accent
        "primary-dark": "#2A41D1",
        "primary-soft": "#EAEDFE",

        accent: "#0EA5A5",     // teal - video/pro capability accent
        "accent-soft": "#E3F8F6",

        danger: "#E23B5D",
        "danger-soft": "#FDEAEF",
        success: "#17A96B",
        "success-soft": "#E6F8EF",
        warn: "#DD8B12",
        "warn-soft": "#FDF3E2",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(23, 26, 41, 0.04), 0 1px 12px rgba(23, 26, 41, 0.04)",
      },
      borderRadius: {
        xl: "14px",
      },
    },
  },
  plugins: [],
};
