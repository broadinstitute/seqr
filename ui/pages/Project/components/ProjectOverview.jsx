import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'

import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'
import ShowIfStaff from 'shared/components/ShowIfStaff'
import EditDatasetsButton from 'shared/components/buttons/EditDatasetsButton'
import EditFamiliesAndIndividualsButton from 'shared/components/buttons/EditFamiliesAndIndividualsButton'

import { getProject, getProjectFamilies, getProjectIndividuals } from '../selectors'


const FAMILY_SIZE_LABELS = {
  0: plural => ` ${plural ? 'families' : 'family'} with no individuals`,
  1: plural => ` ${plural ? 'families' : 'family'} with 1 individual`,
  2: plural => ` ${plural ? 'families' : 'family'} with 2 individuals`,
  3: plural => ` trio${plural ? 's' : ''}`,
  4: plural => ` quad${plural ? 's' : ''}`,
  5: plural => ` ${plural ? 'families' : 'family'} with 5+ individuals`,
}

const SAMPLE_TYPE_LABELS = {
  WES: 'Exome',
  WGS: 'WGS',
  RNA: 'RNA-seq',
}

const DATASET_TYPE_LABELS = {
  VARIANTS: 'callset',
  SV: 'SV callset',
}

const ProjectOverview = (props) => {
  const familySizeHistogram = props.families
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  return (
    <Grid>
      <Grid.Column>
        {/* families */}
        <div>
          {props.families.length} Families, {props.individuals.length} Individuals
        </div>
        <div style={{ padding: '5px 0px 0px 20px' }}>
          {
            sortBy(Object.keys(familySizeHistogram)).map(size =>
              <div key={size}>
                {familySizeHistogram[size]} {FAMILY_SIZE_LABELS[size](familySizeHistogram[size] > 1)}
              </div>)
          }
          {props.project.canEdit ? <span><br /><EditFamiliesAndIndividualsButton /></span> : null }<br />
        </div>
        <div>
          <br />
          Datasets:
          {/*
          <div style={{ padding: '5px 0px 0px 20px' }}>
            {
              props.datasets.length > 0 ?
                Object.keys(SAMPLE_TYPE_LABELS).map(currentSampleType => (
                  <div key={currentSampleType}>
                    {
                      props.datasets.filter(dataset =>
                        dataset.datasetType === 'VARIANTS' && dataset.isLoaded && dataset.sampleType === currentSampleType,
                      ).slice(0, 1).map(dataset =>
                        <div key={dataset.datasetGuid}>
                          {SAMPLE_TYPE_LABELS[dataset.sampleType]} {DATASET_TYPE_LABELS[dataset.datasetType]} - {dataset.sampleGuids.length}  samples
                          {dataset.isLoaded ? ` loaded on ${dataset.loadedDate.slice(0, 10)}` : ' not yet loaded'}
                        </div>,
                      )
                    }
                  </div>
                )) : <div>No Datasets Loaded</div>
            }
            <ShowIfStaff><span><br /><EditDatasetsButton /></span></ShowIfStaff><br />
          </div>
          */}
        </div>
        {/* console.log('hpoTerms', props.hpoTermHistogram) */}
      </Grid.Column>
    </Grid>
  )
}


ProjectOverview.propTypes = {
  project: PropTypes.object,
  families: PropTypes.array.isRequired,
  individuals: PropTypes.array.isRequired,
  datasets: PropTypes.array,
}

const mapStateToProps = state => ({
  project: getProject(state),
  families: getProjectFamilies(state),
  individuals: getProjectIndividuals(state),
  datasets: getProjectDatasets(state),
})


export { ProjectOverview as ProjectOverviewComponent }

export default connect(mapStateToProps)(ProjectOverview)
