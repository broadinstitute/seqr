import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'

import { getLocusListsWithGenes } from 'redux/selectors'
import { Multiselect } from 'shared/components/form/Inputs'
import { moiToMoiInitials } from 'shared/utils/panelAppUtils'
import { PANEL_APP_MOI_OPTIONS } from 'shared/utils/constants'

const EMPTY_LIST = []

class PaMoiDropdown extends React.PureComponent {

  static propTypes = {
    locusList: PropTypes.object,
  }

  moiOptions = () => {
    const { locusList } = this.props

    const initials = locusList.items.reduce((acc, gene) => {
      moiToMoiInitials(gene.pagene?.modeOfInheritance, false).forEach((initial) => {
        acc[initial] = true
      })
      return acc
    }, {}) || {}

    return PANEL_APP_MOI_OPTIONS.map(moi => ({
      ...moi,
      disabled: !initials[moi.value],
    }))
  }

  render() {
    const { value, label, width, locusList, onChange } = this.props || []
    const disabled = !locusList?.items
    return (
      <Multiselect
        label={label}
        value={value}
        width={width}
        inline
        onChange={onChange}
        placeholder="Showing all MOIs as listed in Panel App"
        disabled={disabled}
        options={disabled ? EMPTY_LIST : this.moiOptions()}
        color="violet"
      />
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsWithGenes(state)[ownProps.locus.locusListGuid],
})

export default connect(mapStateToProps)(PaMoiDropdown)
