import React from 'react'
//import { Grid } from 'semantic-ui-react'
//import { connect } from 'react-redux'
//import { bindActionCreators } from 'redux'

class CaseReviewExportPanel extends React.Component
{
  static propTypes = {
    //project: React.PropTypes.object.isRequired,
  }

  render() {
    return <div>
      <div style={{ height: '5px' }} />
      <div style={{ float: 'right', padding: '0px 65px 10px 0px' }}>
        Export Individual Family
      </div>
    </div>
  }
}

export default CaseReviewExportPanel

/*
const mapStateToProps = state => ({
  showCategories: state.projectsTableState.showCategories
})

const mapDispatchToProps = dispatch => bindActionCreators({
  onChange: null,
}, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(NewComponent)
*/
