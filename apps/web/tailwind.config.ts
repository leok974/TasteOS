import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Inter", "sans-serif"],
        serif: ["ui-serif", "Georgia", "serif"]
      },
      colors: {
        base: "#FAF9F6",
      }
    },
  },
  plugins: [],
} satisfies Config;
