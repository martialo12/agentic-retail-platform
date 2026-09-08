/**
 * Google Analytics 4, activé seulement si un identifiant de mesure est fourni.
 *
 * L'identifiant arrive par `/config.js`, réécrit au démarrage du conteneur à
 * partir de `GA_MEASUREMENT_ID` : la même mécanique que l'URL de l'API, pour la
 * même raison — une image ne doit pas être liée à un environnement.
 *
 * Sans identifiant, rien n'est chargé : pas de script tiers, pas de requête, pas
 * de cookie. C'est le comportement en développement et dans les tests.
 *
 * Consentement : `analytics_storage` est refusé par défaut (Consent Mode v2).
 * GA envoie alors des mesures sans cookie, ce qui donne l'audience, la
 * provenance et les événements sans identifier durablement un visiteur. Poser
 * une bannière de consentement, puis appeler `grantAnalyticsConsent()`, fait
 * basculer vers la mesure complète.
 */

type GtagArgs = [string, ...unknown[]]

declare global {
  interface Window {
    dataLayer?: unknown[]
    gtag?: (...args: GtagArgs) => void
  }
}

let enabled = false

const gtag = (...args: GtagArgs): void => {
  window.dataLayer = window.dataLayer || []
  window.dataLayer.push(args)
}

export function initAnalytics(): void {
  const id = window.__ARP_GA_ID__
  if (!id) return

  window.gtag = gtag
  gtag('consent', 'default', {
    analytics_storage: 'denied',
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
  })
  gtag('js', new Date())
  // Les vues sont envoyées à chaque navigation du routeur : une application à
  // page unique n'en déclenche qu'une seule automatiquement, au chargement.
  gtag('config', id, { send_page_view: false })

  const script = document.createElement('script')
  script.async = true
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`
  document.head.appendChild(script)
  enabled = true
}

/** À appeler si vous ajoutez une bannière et que le visiteur accepte. */
export function grantAnalyticsConsent(): void {
  if (!enabled) return
  gtag('consent', 'update', { analytics_storage: 'granted' })
}

export function trackPageView(path: string, title?: string): void {
  if (!enabled) return
  gtag('event', 'page_view', {
    page_path: path,
    page_title: title ?? document.title,
    page_location: window.location.origin + path,
  })
}

/**
 * Un événement métier. Les noms restent stables et lisibles dans l'interface
 * d'Analytics ; les paramètres restent des catégories, jamais le contenu tapé
 * par le visiteur — une question client n'a rien à faire dans un outil de mesure.
 */
export function track(name: string, params: Record<string, unknown> = {}): void {
  if (!enabled) return
  gtag('event', name, params)
}
