import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Loader } from 'semantic-ui-react'

import {
  getProject, getProjectSavedVariantsIsLoading, getProjectSavedVariants, loadProjectVariants,
} from 'redux/rootReducer'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import Variant from 'shared/components/panel/variant/Variant'

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
      <Grid.Row key="histogram" style={{ paddingTop: '20px', paddingBottom: '20px' }}>
        {!this.props.match.params.tag &&
        <Grid.Column textAlign="justified">
          <HorizontalStackedBar
            height={30}
            title="Saved Variants"
            linkPath={this.props.match.url}
            data={this.props.project.variantTagTypes.map((vtt) => {
              return { count: vtt.numTags, ...vtt }
            })}
          />
        </Grid.Column>
          }
      </Grid.Row>,
      this.props.loading ? <Grid.Row key="loader"><Loader key="content" inline="centered" active /></Grid.Row> : null,
      ...this.props.savedVariants.map(variant => <Variant key={variant.variantId} variant={variant} />),
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

