import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'

import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import ShowIfStaff from 'shared/components/ShowIfStaff'
import { getProject, getFamiliesByGuid, getIndividualsByGuid, getDatasetsByGuid } from 'redux/rootReducer'
import EditDatasetsButton from 'shared/components/panel/edit-datasets/EditDatasetsButton'
import EditFamiliesAndIndividualsButton from 'shared/components/panel/edit-families-and-individuals/EditFamiliesAndIndividualsButton'
import SectionHeader from 'shared/components/SectionHeader'


const FAMILY_SIZE_LABELS = {
  1: ' families with 1 individual',
  2: ' families with 2 individuals',
  3: ' trios',
  4: ' quads',
  5: ' families with 5+ individuals',
}

const SAMPLE_TYPE_LABELS = {
  WES: 'Exome',
  WGS: 'WGS',
  RNA: 'RNA-seq',
}

const ANALYSIS_TYPE_LABELS = {
  VARIANTS: 'callset',
  SV: 'SV callset',
}

const ProjectOverview = (props) => {
  const familySizeHistogram = Object.values(props.familiesByGuid)
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  return ([
    <SectionHeader key="header">Overview</SectionHeader>,
    <Grid key="content">
      <Grid.Column>
        {/* families */}
        <div>
          {props.project.numFamilies || Object.keys(props.familiesByGuid).length} Families, {props.project.numIndividuals || Object.keys(props.individualsByGuid).length} Individuals
        </div>
        <div style={{ padding: '5px 0px 0px 20px' }}>
          {
            sortBy(Object.keys(familySizeHistogram)).map(size =>
              <div key={size}>
                {familySizeHistogram[size]} {FAMILY_SIZE_LABELS[size]}
              </div>)
          }
          <ShowIfEditPermissions><span><br /><EditFamiliesAndIndividualsButton /></span></ShowIfEditPermissions><br />
        </div>
        <div>
          <br />
          Datasets:
          <div style={{ padding: '5px 0px 0px 20px' }}>
            {
              Object.values(props.datasetsByGuid).length > 0 ?
                Object.keys(SAMPLE_TYPE_LABELS).map(currentSampleType => (
                  <div key={currentSampleType}>
                    {
                      Object.values(props.datasetsByGuid).filter(dataset =>
                        dataset.analysisType === 'VARIANTS' && dataset.isLoaded && dataset.sampleType === currentSampleType).slice(0, 1).map(dataset =>
                          <div key={dataset.datasetGuid}>
                            {SAMPLE_TYPE_LABELS[dataset.sampleType]} {ANALYSIS_TYPE_LABELS[dataset.analysisType]} - {dataset.sampleGuids.length}  samples
                            {dataset.isLoaded ? ` loaded on ${dataset.loadedDate.slice(0, 10)}` : ' not yet loaded'}
                          </div>)
                    }
                  </div>
              )) : <div>No Datasets Loaded</div>
            }
            <ShowIfStaff><span><br /><EditDatasetsButton /></span></ShowIfStaff><br />
          </div>
        </div>
        {/* console.log('hpoTerms', props.hpoTermHistogram) */}
      </Grid.Column>
    </Grid>,
  ])
}


ProjectOverview.propTypes = {
  project: PropTypes.object.isRequired,
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
  datasetsByGuid: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
  familiesByGuid: getFamiliesByGuid(state),
  individualsByGuid: getIndividualsByGuid(state),
  datasetsByGuid: getDatasetsByGuid(state),
})


export { ProjectOverview as ProjectOverviewComponent }

export default connect(mapStateToProps)(ProjectOverview)
