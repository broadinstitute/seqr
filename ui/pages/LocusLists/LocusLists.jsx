import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Container, Accordion, Header, Icon } from 'semantic-ui-react'

import { loadLocusLists } from 'redux/rootReducer'
import { getLocusListsByGuid, getLocusListsIsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { VerticalSpacer } from 'shared/components/Spacers'
import LocusListTable from './components/LocusListTable'

const ACTIVE_PANELS = [0, 1]

const PANELS = [
  {
    title: (
      <Accordion.Title key="user">
        <Header size="large" dividing><VerticalSpacer height={25} /><Icon name="dropdown" /> My Gene Lists</Header>
      </Accordion.Title>
    ),
    content: { content: <LocusListTable showPublic={false} />, key: 'userTable' },
    key: 'user',
  },
  {
    title: (
      <Accordion.Title key="public">
        <Header size="large" dividing><VerticalSpacer height={25} /><Icon name="dropdown" /> Public Gene Lists</Header>
      </Accordion.Title>
    ),
    content: { content: <LocusListTable showPublic />, key: 'publicTable' },
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

const LocusLists = ({ locusListsByGuid, loading, load }) =>
  <DataLoader content={locusListsByGuid} loading={loading} load={load}>
    <Container>
      <Accordion
        defaultActiveIndex={ACTIVE_PANELS}
        exclusive={false}
        fluid
        panels={PANELS}
      />
    </Container>
  </DataLoader>

LocusLists.propTypes = {
  locusListsByGuid: PropTypes.object,
  loading: PropTypes.bool.isRequired,
  load: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  load: loadLocusLists,
}

const mapStateToProps = state => ({
  locusListsByGuid: getLocusListsByGuid(state),
  loading: getLocusListsIsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(LocusLists)
