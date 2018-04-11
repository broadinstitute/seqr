import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader } from 'semantic-ui-react'

import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import Variants from 'shared/components/panel/variants/Variants'
import {
  getProject, getProjectSavedVariantsIsLoading, getProjectSavedVariants, loadProjectVariants,
} from '../reducers'

class SavedVariants extends React.Component {

  static propTypes = {
    match: PropTypes.object,
    project: PropTypes.object,
    loading: PropTypes.bool,
    savedVariants: PropTypes.array,
    loadProjectVariants: PropTypes.func,
  }

  constructor(props) {
    super(props)

    props.loadProjectVariants(props.match.params.tag)
  }

  render() {
    return [
      <div key="histogram" style={{ paddingTop: '20px', paddingBottom: '20px' }}>
        {!this.props.match.params.tag &&
          <HorizontalStackedBar
            height={30}
            title="Saved Variants"
            linkPath={this.props.match.url}
            data={this.props.project.variantTagTypes.map((vtt) => {
              return { count: vtt.numTags, ...vtt }
            })}
          />
        }
      </div>,
      this.props.loading ? <Loader key="content" inline="centered" active /> : null,
      this.props.savedVariants ?
        <div key="variants" style={{ paddingTop: '20px' }}><Variants variants={this.props.savedVariants} /></div>
        : null,
    ]
  }
}

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state),
  loading: getProjectSavedVariantsIsLoading(state),
  savedVariants: getProjectSavedVariants(state, ownProps.match.params.tag),
})

const mapDispatchToProps = {
  loadProjectVariants,
}

export default connect(mapStateToProps, mapDispatchToProps)(SavedVariants)

