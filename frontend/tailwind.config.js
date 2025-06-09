/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'llm-primary': '#0066CC',
        'llm-secondary': '#00AA55',
        'llm-accent': '#FF6633',
      },
    },
  },
  plugins: [],
}