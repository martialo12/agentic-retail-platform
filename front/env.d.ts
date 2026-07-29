/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Injected by /config.js, which the container rewrites from API_BASE at
// start-up. Absent in development, where the Vite variable takes over.
interface Window {
  __ARP_API_BASE__?: string
}
