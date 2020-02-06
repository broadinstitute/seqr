import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Header } from 'semantic-ui-react'

import { loadProject } from 'redux/rootReducer'
import { getProjectsByGuid, getSamplesGroupedByProjectGuid, getProjectsIsLoading } from 'redux/selectors'
import { Select, InlineToggle } from 'shared/components/form/Inputs'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import VariantSearchFormContainer from 'shared/components/panel/search/VariantSearchFormContainer'
import VariantSearchFormPanels, {
  STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
} from 'shared/components/panel/search/VariantSearchFormPanels'
import { AddProjectButton, ProjectFilter } from 'shared/components/panel/search/ProjectsField'
import VariantSearchResults from 'pages/Search/components/VariantSearchResults' // TODO move to shared
import { InlineHeader } from 'shared/components/StyledComponents'
import { INHERITANCE_FILTER_OPTIONS, ALL_INHERITANCE_FILTER } from 'shared/utils/constants'
import { STAFF_SEARCH_FORM_NAME, INCLUDE_ALL_PROJECTS } from '../constants'
import { loadProjectGroupContext } from '../reducers'
import { getSearchIncludeAllProjectsInput } from '../selectors'

const mapFormStateToProps = state => ({
  includeAllProjects: getSearchIncludeAllProjectsInput(state),
})

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

const INCLUDE_ALL_PROJECTS_FIELD = {
  name: INCLUDE_ALL_PROJECTS,
  component: InlineToggle,
  fullHeight: true,
}

const INHERITANCE_PANEL = {
  name: 'inheritance.mode',
  headerProps: {
    title: 'Inheritance',
    inputProps: {
      component: Select,
      options: INHERITANCE_FILTER_OPTIONS,
      format: val => val || ALL_INHERITANCE_FILTER,
    },
  },
  helpText: <Header disabled content="Custom inheritance search is disabled for multi-family searches" />,
}

const PANELS = [
  INHERITANCE_PANEL, STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
]

const CustomSearch = ({ match, history, includeAllProjects, ...props }) =>
  <Grid>
    <Grid.Row>
      <Grid.Column width={16}>
        <VariantSearchFormContainer history={history} resultsPath={match.url} form={STAFF_SEARCH_FORM_NAME}>
          <InlineHeader content="Include All Projects:" /> {configuredField(INCLUDE_ALL_PROJECTS_FIELD)}
          {includeAllProjects ? null : configuredField(PROJECT_FAMILIES_FIELD)}
          <VariantSearchFormPanels panels={PANELS} />
        </VariantSearchFormContainer>
      </Grid.Column>
    </Grid.Row>
    {match.params.searchHash && <VariantSearchResults match={match} history={history} {...props} />}
  </Grid>

CustomSearch.propTypes = {
  match: PropTypes.object,
  history: PropTypes.object,
  includeAllProjects: PropTypes.bool,
}

export default connect(mapFormStateToProps)(CustomSearch)
