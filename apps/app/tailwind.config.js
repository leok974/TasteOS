import { tailwindPreset } from '@tasteos/design'

/** @type {import('tailwindcss').Config} */
export default {
  presets: [tailwindPreset],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    '../../packages/ui/src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
