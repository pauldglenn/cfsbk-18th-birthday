import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { defineConfig as defineVitestConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})

// Vitest config for TS type checking
export const vitest = defineVitestConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
  },
})
