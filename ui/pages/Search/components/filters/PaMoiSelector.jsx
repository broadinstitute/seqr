import PropTypes from 'prop-types'
import React from 'react'
import { Multiselect } from 'shared/components/form/Inputs'
import { moiToMoiInitials, formatPanelAppItems } from 'shared/utils/panelAppUtils'
import { PANEL_APP_MOI_OPTIONS } from 'shared/utils/constants'

export default class PaMoiDropdown extends React.PureComponent {

  static propTypes = {
    locus: PropTypes.object,
    onChange: PropTypes.func,
  }

  handleMOIselect = (selectedMOIs) => {
    const { locus, onChange } = this.props
    const { locusList } = locus

    const panelAppItems = formatPanelAppItems(
      locusList.items?.filter((item) => {
        let result = true
        const initials = moiToMoiInitials(item.pagene?.modeOfInheritance)
        if (initials.length === 0) initials.push('other')
        if (selectedMOIs && selectedMOIs.length !== 0) {
          result = selectedMOIs.some(moi => initials.includes(moi))
        }
        return result
      }),
    )

    onChange({ ...panelAppItems })
  }

  moiOptions = () => {
    const { locus } = this.props
    const { locusList } = locus

    const initials = locusList.items?.reduce((acc, gene) => {
      moiToMoiInitials(gene.pagene?.modeOfInheritance).forEach((initial) => {
        acc[initial] = true
      })
      if (moiToMoiInitials(gene.pagene?.modeOfInheritance).length === 0) {
        acc.other = true
      }
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
