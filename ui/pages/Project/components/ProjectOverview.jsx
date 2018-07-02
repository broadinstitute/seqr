import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'

import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'
import EditFamiliesAndIndividualsButton from 'shared/components/buttons/EditFamiliesAndIndividualsButton'
import EditDatasetsButton from 'shared/components/buttons/EditDatasetsButton'

import { getProject, getProjectFamiliesByGuid, getProjectIndividualsByGuid } from 'pages/Project/selectors'


const FAMILY_SIZE_LABELS = {
  0: plural => ` ${plural ? 'families' : 'family'} with no individuals`,
  1: plural => ` ${plural ? 'families' : 'family'} with 1 individual`,
  2: plural => ` ${plural ? 'families' : 'family'} with 2 individuals`,
  3: plural => ` trio${plural ? 's' : ''}`,
  4: plural => ` quad${plural ? 's' : ''}`,
  5: plural => ` ${plural ? 'families' : 'family'} with 5+ individuals`,
}

const ProjectOverview = (props) => {
  const familySizeHistogram = Object.values(props.familiesByGuid)
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  return (
    <Grid>
      <Grid.Column>
        <div>
          {Object.keys(props.familiesByGuid).length} Families, {Object.keys(props.individualsByGuid).length} Individuals
        </div>
        <div style={{ padding: '5px 0px 0px 20px' }}>
          {
            sortBy(Object.keys(familySizeHistogram)).map(size =>
              <div key={size}>
                {familySizeHistogram[size]} {FAMILY_SIZE_LABELS[size](familySizeHistogram[size] > 1)}
              </div>)
          }
        </div>
        {props.project.canEdit ? <div><br /><EditFamiliesAndIndividualsButton /> | <EditDatasetsButton /></div> : null }
      </Grid.Column>
    </Grid>
  )
}


ProjectOverview.propTypes = {
  project: PropTypes.object,
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
  familiesByGuid: getProjectFamiliesByGuid(state),
  individualsByGuid: getProjectIndividualsByGuid(state),
})


export { ProjectOverview as ProjectOverviewComponent }

export default connect(mapStateToProps)(ProjectOverview)
