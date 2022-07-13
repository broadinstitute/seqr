import PropTypes from 'prop-types'
import React from 'react'
import { Multiselect } from 'shared/components/form/Inputs'
import { semanticShouldUpdate } from 'shared/utils/semanticUtils'
import { moiToMoiInitials, panelAppLocusListReducer } from 'shared/utils/panelAppUtils'
import { PANEL_APP_MOI_OPTIONS } from 'shared/utils/constants'

class PaMoiDropdown extends React.Component {

  static propTypes = {
    locus: PropTypes.object,
    onChange: PropTypes.func,
  }

  shouldComponentUpdate(nextProps, nextState) {
    return semanticShouldUpdate(this, nextProps, nextState)
  }

  handleMOIselect = (selectedMOIs) => {
    const { locus, onChange } = this.props
    const { locusList } = locus

    const panelAppItems = locusList.items?.filter((item) => {
      let result = true
      if (selectedMOIs && selectedMOIs.length !== 0) {
        const initials = moiToMoiInitials(item.pagene?.modeOfInheritance)
        if (initials.length === 0) initials.push('other')
        result = selectedMOIs.filter(moi => initials.includes(moi)).length !== 0
      }
      return result
    }).reduce(panelAppLocusListReducer, {})

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

export default React.memo(props => (
  <PaMoiDropdown
    {...props}
    inline
  />
))
