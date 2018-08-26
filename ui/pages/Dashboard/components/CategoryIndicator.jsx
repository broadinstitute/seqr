import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import randomMC from 'random-material-color'

import { ColoredIcon } from 'shared/components/StyledComponents'
import { getProjectCategoriesByGuid } from 'redux/selectors'
import EditProjectCategoriesModal from './EditProjectCategoriesModal'

class CategoryIndicator extends React.Component {

  static propTypes = {
    project: PropTypes.object.isRequired,
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
    this.color = this.categoryGuids.length === 0 ? '#ccc' : randomMC.getColor({ shades: ['300', '400', '500', '600', '700', '800'], text: this.categoryNames.join(',') })
  }

  render() {
    const StarButton = (
      <a role="button" tabIndex="0" style={{ cursor: 'pointer' }}>
        <ColoredIcon name={`${this.categoryGuids.length === 0 ? 'empty ' : ''}star`} color={this.color} />
      </a>
    )

    let popup
    if (this.categoryGuids.length > 0) {
      popup = {
        content: (
          <div>
            <div>Categories:</div><br />
            <div>{this.categoryNames.map(name => <div key={name}>{name}</div>)}</div>
          </div>
        ),
        position: 'top center',
        size: 'small',
      }
    }

    return <EditProjectCategoriesModal project={this.props.project} trigger={StarButton} popup={popup} triggerName="categoryIndicator" />
  }
}

export { CategoryIndicator as CategoryIndicatorComponent }

const mapStateToProps = state => ({ projectCategoriesByGuid: getProjectCategoriesByGuid(state) })

export default connect(mapStateToProps)(CategoryIndicator)

