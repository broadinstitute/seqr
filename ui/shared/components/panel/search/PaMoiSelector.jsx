import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'

import { getLocusListsWithGenes } from 'redux/selectors'
import { Multiselect } from 'shared/components/form/Inputs'
import { moiToMoiInitials, formatPanelAppItems } from 'shared/utils/panelAppUtils'
import { PANEL_APP_MOI_OPTIONS } from 'shared/utils/constants'

class PaMoiDropdown extends React.PureComponent {

  static propTypes = {
    locusList: PropTypes.object,
    onChange: PropTypes.func,
  }

  handleMOIselect = (selectedMOIs) => {
    const { locusList, onChange } = this.props

    const panelAppItems = formatPanelAppItems(
      locusList.items?.filter((item) => {
        let result = true
        const initials = moiToMoiInitials(item.pagene?.modeOfInheritance, false)
        if (selectedMOIs && selectedMOIs.length !== 0) {
          result = selectedMOIs.some(moi => initials.includes(moi))
        }
        return result
      }),
    )

    onChange({ ...panelAppItems })
  }

  moiOptions = () => {
    const { locusList } = this.props

    const initials = locusList.items?.reduce((acc, gene) => {
      moiToMoiInitials(gene.pagene?.modeOfInheritance).forEach((initial) => {
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
    const { selectedMOIs, label, width } = this.props || []
    return (
      <Multiselect
        label={label}
        value={selectedMOIs}
        width={width}
        inline
        onChange={this.handleMOIselect}
        placeholder="Showing all MOIs as listed in Panel App"
        options={this.moiOptions()}
        color="violet"
      />
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsWithGenes(state)[ownProps.locus.locusListGuid],
})

export default connect(mapStateToProps)(PaMoiDropdown)
