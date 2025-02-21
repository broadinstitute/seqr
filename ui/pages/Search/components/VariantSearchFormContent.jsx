import React from 'react'
import PropTypes from 'prop-types'
import { FormSpy } from 'react-final-form'
import styled from 'styled-components'
import { Header, Grid } from 'semantic-ui-react'

import { configuredField } from 'shared/components/form/FormHelpers'
import VariantSearchFormPanels from './VariantSearchFormPanels'
import { SavedSearchDropdown } from './SavedSearch'
import ProjectFamiliesField from './filters/ProjectFamiliesField'

const SavedSearchColumn = styled(Grid.Column)`
  font-size: 0.75em;
`

const SAVED_SEARCH_FIELD = {
  name: 'search',
  component: SavedSearchDropdown,
  format: val => val || {},
}

const VariantSearchFormContent = React.memo(({ inheritance, noEditProjects }) => (
  <div>
    {!noEditProjects && <ProjectFamiliesField />}
    <Header size="huge" block>
      <Grid padded="horizontally" relaxed>
        <Grid.Row>
          <Grid.Column width={8} verticalAlign="middle">Select a Saved Search (Recommended)</Grid.Column>
          <SavedSearchColumn width={4} floated="right" textAlign="right">
            {configuredField(SAVED_SEARCH_FIELD)}
          </SavedSearchColumn>
        </Grid.Row>
      </Grid>
    </Header>
    <Header content="Customize Search:" />
    <VariantSearchFormPanels inheritance={inheritance} />
  </div>
))

VariantSearchFormContent.propTypes = {
  inheritance: PropTypes.object,
  noEditProjects: PropTypes.bool,
}

const SUBSCRIPTION = { values: true }

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <VariantSearchFormContent
        {...props}
        projectFamilies={values.projectFamilies}
        inheritance={values.search?.inheritance}
      />
    )}
  </FormSpy>
)
