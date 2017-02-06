import React from 'react'
import { Icon, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import randomMC from 'random-material-color'

import { showModal } from '../reducers/rootReducer'
import { EDIT_CATEGORY_MODAL } from '../constants'

class CategoryIndicator extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    showModal: React.PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    this.cacheBeforeRender(props)
  }
  componentWillReceiveProps(nextProps) {
    this.cacheBeforeRender(nextProps)
  }

  cacheBeforeRender(props) {
    this.guids = props.project.projectCategoryGuids
    this.names = this.guids.map(guid => (props.projectCategoriesByGuid[guid] && props.projectCategoriesByGuid[guid].name) || guid)
    this.names.sort()
    this.color = randomMC.getColor({ shades: ['300', '400', '500', '600', '700', '800'], text: this.names.join(',') })
  }

  render() {
    if (this.guids.length === 0) {
      return null
    }

    return <Popup
      trigger={
        <a href="#." onClick={() => { this.props.showModal(EDIT_CATEGORY_MODAL, this.props.project.projectGuid) }}>
          <Icon name="star" style={{ color: this.color }} />
        </a>
      }
      content={<div>
        <div>Categories:</div><br />
        <div>{this.names.map(name => <div key={name}>{name}</div>)}</div>
      </div>}
      positioning="top center"
      size="small"
    />
  }
}


const mapStateToProps = state => ({ projectCategoriesByGuid: state.projectCategoriesByGuid })

const mapDispatchToProps = dispatch => bindActionCreators({ showModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(CategoryIndicator)

