import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import {
  Grid,
  // Loader
} from 'semantic-ui-react'

import { getProject } from 'redux/rootReducer'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'

const SavedVariants = ({ match, project }) =>
  <Grid.Row>
    <Grid.Column textAlign="justified" style={{ paddingTop: '20px' }}>
      {
        match.params.tag ?
          project.variantTagTypes.find(vtt => vtt.name === match.params.tag).numTags
          : <HorizontalStackedBar
            // width={100}
            height={30}
            title="Saved Variants"
            linkPath={match.url}
            data={project.variantTagTypes.map((vtt) => { return { count: vtt.numTags, ...vtt } })}
          />
      }
    </Grid.Column>
  </Grid.Row>


SavedVariants.propTypes = {
  match: PropTypes.object,
  project: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(SavedVariants)

