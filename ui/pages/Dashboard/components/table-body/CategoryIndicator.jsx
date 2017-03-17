import React from 'react'
import { Icon, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import randomMC from 'random-material-color'

import { showModal } from '../../reducers/rootReducer'
import { EDIT_CATEGORY_MODAL } from '../../constants'

class CategoryIndicator extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    showModal: React.PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    this.computeValuesBeforeRender(props)
  }

  componentWillReceiveProps(nextProps) {
    this.computeValuesBeforeRender(nextProps)
  }

  computeValuesBeforeRender(props) {
    this.categoryGuids = props.project.projectCategoryGuids
    this.categoryNames = this.categoryGuids.map(guid => (props.projectCategoriesByGuid[guid] && props.projectCategoriesByGuid[guid].name) || guid)
    this.categoryNames.sort()
    this.color = randomMC.getColor({ shades: ['300', '400', '500', '600', '700', '800'], text: this.categoryNames.join(',') })
  }

  render() {
    if (this.categoryGuids.length === 0) {
      return null
    }

    return <Popup
      trigger={
        <a tabIndex="0" onClick={() => { this.props.showModal(EDIT_CATEGORY_MODAL, this.props.project.projectGuid) }} style={{ cursor: 'pointer' }}>
          <Icon name="star" style={{ color: this.color }} />
        </a>
      }
      content={
        <div>
          <div>Categories:</div><br />
          <div>{this.categoryNames.map(name => <div key={name}>{name}</div>)}</div>
        </div>
      }
      positioning="top center"
      size="small"
    />
  }
}

export { CategoryIndicator as CategoryIndicatorComponent }

const mapStateToProps = state => ({ projectCategoriesByGuid: state.projectCategoriesByGuid })

const mapDispatchToProps = dispatch => bindActionCreators({ showModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(CategoryIndicator)

