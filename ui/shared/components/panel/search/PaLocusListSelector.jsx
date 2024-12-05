import React, { useState } from 'react'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { useSelector } from 'react-redux'
import { useFormState } from 'react-final-form'
import { getLocusListsWithGenes } from 'redux/selectors'
import { moiToMoiInitials, formatPanelAppItems } from 'shared/utils/panelAppUtils'
import PropTypes from 'prop-types'

const PaLocusListSelector = ({ locus, onChange, color, value, ...props }) => {
  const [prevValue, setPrevValue] = useState(value)
  const locusList = useSelector(state => getLocusListsWithGenes(state)[locus.locusListGuid])
  const selectedMOIs = Object.values(useFormState().values?.search?.locus?.selectedMOIs ?? {}) || []

  const panelAppItems = formatPanelAppItems(
    locusList?.items?.filter((item) => {
      let result = true
      const initials = moiToMoiInitials(item.pagene?.modeOfInheritance, false)
      if (selectedMOIs && selectedMOIs.length !== 0) {
        result = selectedMOIs.some(moi => initials.includes(moi))
      }
      return result
    }),
  )

  // TODO this call to onChange during render might be an issue
  if (panelAppItems[color] !== prevValue) {
    setPrevValue(panelAppItems[color])
    onChange(panelAppItems[color])
  }

  return (
    <BaseSemanticInput
      {...props}
      value={value}
      onChange={onChange}
    />
  )
}

PaLocusListSelector.propTypes = {
  locus: PropTypes.object,
  onChange: PropTypes.func,
  color: PropTypes.string,
  value: PropTypes.string,
}

export default PaLocusListSelector
