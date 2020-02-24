import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { Dropdown } from 'shared/components/form/Inputs'
import { LocusListItemsLoader } from 'shared/components/LocusListLoader'
import { getSearchedProjectsLocusListOptions } from '../../selectors'


class BaseLocusListDropdown extends React.Component
{
  render() {
    const { locusList, projectLocusListOptions, onChange } = this.props
    return (
      <div>
        <Dropdown
          inline
          selection
          label="Gene List"
          value={locusList.locusListGuid}
          onChange={locusListGuid => onChange({ locusListGuid })}
          options={[{ text: 'None', value: null }].concat(projectLocusListOptions)}
        />
      </div>
    )
  }

  componentWillUpdate(nextProps) {
    if (nextProps.locusList.rawItems !== this.props.locusList.rawItems) {
      const { locusListGuid, rawItems } = nextProps.locusList
      this.props.onChange({ locusListGuid, rawItems })
    }
  }

  shouldComponentUpdate(nextProps) {
    return nextProps.projectLocusListOptions !== this.props.projectLocusListOptions ||
      nextProps.onChange !== this.props.onChange ||
      nextProps.locusList.locusListGuid !== this.props.locusList.locusListGuid ||
      (!!this.props.locusList.locusListGuid && nextProps.locusList.rawItems !== this.props.locusList.rawItems)
  }
}

const mapStateToProps = state => ({
  projectLocusListOptions: getSearchedProjectsLocusListOptions(state),
})

BaseLocusListDropdown.propTypes = {
  locusList: PropTypes.object,
  projectLocusListOptions: PropTypes.array,
  onChange: PropTypes.func,
}

const LocusListDropdown = connect(mapStateToProps)(BaseLocusListDropdown)

const LocusListSelector = React.memo(({ value, ...props }) =>
  <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
    <LocusListDropdown {...props} />
  </LocusListItemsLoader>,
)

LocusListSelector.propTypes = {
  value: PropTypes.object,
}

export default LocusListSelector
