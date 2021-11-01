import { lazy } from 'react'

// lazy load infrequently accessed public info pages
const MatchmakerDisclaimer = lazy(() => import('./components/MatchmakerDisclaimer'))
const MatchmakerInfo = lazy(() => import('./components/MatchmakerInfo'))
const PrivacyPolicy = lazy(() => import('./components/PrivacyPolicy'))
const TermsOfService = lazy(() => import('./components/TermsOfService'))

export default [
  { path: '/matchmaker/matchbox', component: MatchmakerInfo },
  { path: '/matchmaker/disclaimer', component: MatchmakerDisclaimer },
  { path: '/privacy_policy', component: PrivacyPolicy },
  { path: '/terms_of_service', component: TermsOfService },
]
