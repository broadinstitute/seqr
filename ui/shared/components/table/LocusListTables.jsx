import React from 'react'
import { Header } from 'semantic-ui-react'

import { VerticalSpacer } from '../Spacers'
import LocusListTable from './LocusListTable'

export default props =>
  <div>
    <VerticalSpacer height={5} />
    <Header size="large" dividing content="My Gene Lists" />
    <LocusListTable {...props} showPublic={false} />
    <Header size="large" dividing content="Public Gene Lists" />
    <LocusListTable {...props} showPublic />
  </div>
