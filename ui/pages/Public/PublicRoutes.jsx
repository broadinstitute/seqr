import { lazy } from 'react'

import { MATCHMAKER_PATH, FAQ_PATH, PRIVACY_PATH, TOS_PATH } from 'shared/utils/constants'

// lazy load infrequently accessed public info pages
const MatchmakerDisclaimer = lazy(() => import('./components/MatchmakerDisclaimer'))
const MatchmakerInfo = lazy(() => import('./components/MatchmakerInfo'))
const Faq = lazy(() => import('./components/Faq'))
const PrivacyPolicy = lazy(() => import('./components/PrivacyPolicy'))
const TermsOfService = lazy(() => import('./components/TermsOfService'))

export default [
  { path: `${MATCHMAKER_PATH}/matchbox`, component: MatchmakerInfo },
  { path: `${MATCHMAKER_PATH}/disclaimer`, component: MatchmakerDisclaimer },
  { path: FAQ_PATH, component: Faq },
  { path: PRIVACY_PATH, component: PrivacyPolicy },
  { path: TOS_PATH, component: TermsOfService },
]
