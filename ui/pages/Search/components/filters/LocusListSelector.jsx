import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { Dropdown } from 'shared/components/form/Inputs'
import { LocusListItemsLoader } from 'shared/components/LocusListLoader'
import { getSearchedProjectsLocusListOptions } from '../../selectors'

class BaseLocusListDropdown extends React.Component {

  static propTypes = {
    locusList: PropTypes.object,
    projectLocusListOptions: PropTypes.arrayOf(PropTypes.object),
    onChange: PropTypes.func,
  }

  shouldComponentUpdate(nextProps) {
    const { locusList, projectLocusListOptions, onChange } = this.props
    return nextProps.projectLocusListOptions !== projectLocusListOptions ||
      nextProps.onChange !== onChange ||
      nextProps.locusList.locusListGuid !== locusList.locusListGuid ||
      (!!locusList.locusListGuid && nextProps.locusList.rawItems !== locusList.rawItems)
  }

  componentDidUpdate(prevProps) {
    const { locusList, onChange } = this.props
    if (prevProps.locusList.rawItems !== locusList.rawItems) {
      const { locusListGuid, rawItems } = locusList
      onChange({ locusListGuid, rawItems })
    }
  }

  onChange = (locusListGuid) => {
    const { onChange } = this.props
    onChange({ locusListGuid })
  }

  render() {
    const { locusList, projectLocusListOptions } = this.props
    return (
      <div>
        <Dropdown
          inline
          selection
          label="Gene List"
          value={locusList.locusListGuid}
          onChange={this.onChange}
          options={projectLocusListOptions}
        />
      </div>
    )
  }

}

const mapStateToProps = state => ({
  projectLocusListOptions: getSearchedProjectsLocusListOptions(state),
})

const LocusListDropdown = connect(mapStateToProps)(BaseLocusListDropdown)

const LocusListSelector = React.memo(({ value, ...props }) => (
  <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
    <LocusListDropdown {...props} />
  </LocusListItemsLoader>
))

LocusListSelector.propTypes = {
  value: PropTypes.object,
}

export default LocusListSelector
