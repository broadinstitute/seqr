import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'

import { Dropdown } from 'shared/components/form/Inputs'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import VariantSearchFormContainer from 'shared/components/panel/search/VariantSearchFormContainer'
import VariantSearchFormPanels, {
  STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
} from 'shared/components/panel/search/VariantSearchFormPanels'
import VariantSearchResults from 'pages/Search/components/VariantSearchResults'
import { InlineHeader } from 'shared/components/StyledComponents'
import { INHERITANCE_FILTER_OPTIONS } from 'shared/utils/constants'

const SEARCH_FORM_NAME = 'customVariantSearch'

const PANELS = [
  STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
]

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
          <div>TODO Project filter</div>
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
