import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { Dropdown } from 'shared/components/form/Inputs'
import { LocusListItemsLoader } from 'shared/components/LocusListLoader'
import { getSearchedProjectsLocusLists } from '../../selectors'


class BaseLocusListDropdown extends React.Component
{
  render() {
    const { locusList, projectLocusLists, onChange } = this.props
    return (
      <Dropdown
        inline
        selection
        label="Gene List"
        value={locusList.locusListGuid}
        onChange={locusListGuid => onChange({ locusListGuid })}
        options={projectLocusLists.map(ll => ({ text: ll.name, value: ll.locusListGuid }))}
      />
    )
  }

  componentWillUpdate(nextProps) {
    if (nextProps.locusList.rawItems !== this.props.locusList.rawItems) {
      const { locusListGuid, rawItems } = nextProps.locusList
      this.props.onChange({ locusListGuid, rawItems })
    }
  }
}

const mapStateToProps = state => ({
  projectLocusLists: getSearchedProjectsLocusLists(state),
})

BaseLocusListDropdown.propTypes = {
  locusList: PropTypes.object,
  projectLocusLists: PropTypes.array,
  onChange: PropTypes.func,
}

const LocusListDropdown = connect(mapStateToProps)(BaseLocusListDropdown)

const LocusListSelector = ({ value, ...props }) =>
  <LocusListItemsLoader locusListGuid={value.locusListGuid} reloadOnIdUpdate content hideLoading>
    <LocusListDropdown {...props} />
  </LocusListItemsLoader>

LocusListSelector.propTypes = {
  value: PropTypes.object,
}

export default LocusListSelector
