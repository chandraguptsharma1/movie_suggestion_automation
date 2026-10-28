import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontSize: {
        xs: ['0.6875rem', { lineHeight: '1.5' }],
        sm: ['0.8125rem', { lineHeight: '1.5' }],
        base: ['0.875rem', { lineHeight: '1.5' }],
        lg: ['1rem', { lineHeight: '1.4' }],
        xl: ['1.125rem', { lineHeight: '1.35' }],
        '2xl': ['1.375rem', { lineHeight: '1.3' }],
        '3xl': ['1.625rem', { lineHeight: '1.25' }],
        '4xl': ['1.875rem', { lineHeight: '1.2' }],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
    },
  },
  plugins: [],
};
export default config;
