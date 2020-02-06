import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'

import { loadProject } from 'redux/rootReducer'
import { getProjectsByGuid, getSamplesGroupedByProjectGuid, getProjectsIsLoading } from 'redux/selectors'
import { Dropdown } from 'shared/components/form/Inputs'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import VariantSearchFormContainer from 'shared/components/panel/search/VariantSearchFormContainer'
import VariantSearchFormPanels, {
  STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
} from 'shared/components/panel/search/VariantSearchFormPanels'
import { AddProjectButton, ProjectFilter } from 'shared/components/panel/search/ProjectsField'
import VariantSearchResults from 'pages/Search/components/VariantSearchResults' // TODO move to shared
import { InlineHeader } from 'shared/components/StyledComponents'
import { INHERITANCE_FILTER_OPTIONS } from 'shared/utils/constants'
import { loadProjectGroupContext } from '../reducers'


const SEARCH_FORM_NAME = 'customVariantSearch'

const PANELS = [
  STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
]

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.value],
  projectSamples: getSamplesGroupedByProjectGuid(state)[ownProps.value],
  loading: getProjectsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProject,
}

const mapAddProjectDispatchToProps = {
  addProjectGroup: loadProjectGroupContext,
}

const PROJECT_FAMILIES_FIELD = {
  name: 'projectGuids',
  component: connect(mapStateToProps, mapDispatchToProps)(ProjectFilter),
  addArrayElement: connect(null, mapAddProjectDispatchToProps)(AddProjectButton),
  isArrayField: true,
}

const INHERITANCE_FIELD = {
  name: 'inheritance.mode',
  label: <InlineHeader content="Inheritance" />,
  component: Dropdown,
  inline: true,
  selection: true,
  placeholder: 'All',
  options: INHERITANCE_FILTER_OPTIONS,
}

const CustomSearch = props =>
  <Grid>
    <Grid.Row>
      <Grid.Column width={16}>
        <VariantSearchFormContainer history={props.history} resultsPath={props.match.url} form={SEARCH_FORM_NAME}>
          {configuredField(PROJECT_FAMILIES_FIELD)}
          {configuredField(INHERITANCE_FIELD)}
          <VariantSearchFormPanels panels={PANELS} />
        </VariantSearchFormContainer>
      </Grid.Column>
    </Grid.Row>
    {props.match.params.searchHash && <VariantSearchResults {...props} />}
  </Grid>

CustomSearch.propTypes = {
  match: PropTypes.object,
  history: PropTypes.object,
}

export default CustomSearch
