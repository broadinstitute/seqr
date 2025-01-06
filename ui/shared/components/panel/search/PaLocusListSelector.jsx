import React from 'react'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { useSelector } from 'react-redux'
import { getLocusListsWithGenes } from 'redux/selectors'
import { moiToMoiInitials, formatPanelAppItems } from 'shared/utils/panelAppUtils'
import PropTypes from 'prop-types'
import { OnChange } from 'react-final-form-listeners'

const filterPanelAppItems = (locusList, selectedMOIs, color) => formatPanelAppItems(
  locusList?.items?.filter((item) => {
    let result = true
    const initials = moiToMoiInitials(item.pagene?.modeOfInheritance, false)
    if (selectedMOIs.length > 0) {
      result = selectedMOIs.some(moi => initials.includes(moi))
    }
    return result
  }),
)[color]

const PaLocusListSelector = ({ locus, onChange, color, value, ...props }) => {
  const locusList = useSelector(state => getLocusListsWithGenes(state)[locus.locusListGuid])

  const onSelectedMOIChange = (selectedMOIs) => {
    const panelAppItems = filterPanelAppItems(locusList, selectedMOIs, color)
    onChange(panelAppItems)
  }

  return (
    <span>
      <OnChange name="search.locus.selectedMOIs">
        {(newSelectedMOI) => {
          onSelectedMOIChange(newSelectedMOI)
        }}
      </OnChange>
      <BaseSemanticInput
        {...props}
        value={value}
        onChange={onChange}
      />
    </span>
  )
}

PaLocusListSelector.propTypes = {
  locus: PropTypes.object,
  onChange: PropTypes.func,
  color: PropTypes.string,
  value: PropTypes.string,
}

export default PaLocusListSelector
