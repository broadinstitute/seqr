import React from 'react'
import { Loader } from 'semantic-ui-react'

// helper component to lazily load pedigree image, as it uses large js libraries that are not used anywhere else
const LazyPedigreeImagePanel = React.lazy(() => import('./LazyPedigreeImagePanel'))

export default props => <React.Suspense fallback={<Loader />}><LazyPedigreeImagePanel {...props} /></React.Suspense>
