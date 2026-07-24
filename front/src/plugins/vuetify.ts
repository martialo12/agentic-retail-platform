import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

import { createVuetify } from 'vuetify'

/**
 * "Maison" — a warm, premium palette for governed retail AI.
 *
 * `stamp` (amber) is reserved for governance outcomes — a refused tool call, an
 * escalation. Nothing else in the interface may use it. The scarcity is what
 * gives a refusal its weight when it appears. `ok` (green) carries both "the
 * system is operating within its rules" and the brand's quiet thread.
 */
export default createVuetify({
  theme: {
    defaultTheme: 'console',
    themes: {
      console: {
        dark: false,
        colors: {
          background: '#FBFAF7',
          surface: '#FFFFFF',
          primary: '#1A1712',
          secondary: '#8C8578',
          stamp: '#B4530A',
          ok: '#16624B',
          error: '#9B2C1B',
          warning: '#B4530A',
        },
      },
    },
  },
  defaults: {
    VCard: { flat: true, border: true, rounded: 'sm' },
    VBtn: { variant: 'flat', rounded: 'sm' },
    VTextField: { variant: 'outlined', density: 'comfortable', hideDetails: 'auto' },
  },
})
