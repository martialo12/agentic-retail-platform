import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

import { createVuetify } from 'vuetify'

/**
 * A control-room palette, not a dashboard one.
 *
 * `stamp` is reserved for governance outcomes — a refused tool call, an
 * escalation. Nothing else in the interface may use it. The scarcity is what
 * gives a refusal its weight when it appears.
 */
export default createVuetify({
  theme: {
    defaultTheme: 'console',
    themes: {
      console: {
        dark: false,
        colors: {
          background: '#F6F7F8',
          surface: '#FFFFFF',
          primary: '#14181F',
          secondary: '#6B7480',
          stamp: '#7A1F4B',
          ok: '#1F6F5C',
          error: '#8A2B1F',
          warning: '#7A1F4B',
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
