import React from 'react'
import PropTypes from 'prop-types'
import { Accordion, Header, Icon } from 'semantic-ui-react'

import { VerticalSpacer } from '../Spacers'
import LocusListTable from './LocusListTable'

const ACTIVE_PANELS = [0, 1]

const PANELS = [
  {
    title: 'My Gene Lists',
    contentProps: { showPublic: false },
    key: 'user',
  },
  {
    title: 'Public Gene Lists',
    contentProps: { showPublic: true },
    key: 'public',
  },
]

const PanelHeader = ({ title }) =>
  <Header size="large" dividing>
    <VerticalSpacer height={25} />
    <Icon name="dropdown" /> {title}
  </Header>

PanelHeader.propTypes = {
  title: PropTypes.string,
}

export default (props) => {
  const panels = PANELS.map(({ contentProps, title, key }) => ({
    content: { content: <LocusListTable {...props} {...contentProps} />, key: `${key}-content` },
    title: (
      <Accordion.Title key={`${key}-title`}>
        <Header size="large" dividing><VerticalSpacer height={25} /><Icon name="dropdown" /> {title}</Header>
      </Accordion.Title>
    ),
  }))
  return <Accordion defaultActiveIndex={ACTIVE_PANELS} exclusive={false} fluid panels={panels} />
}
