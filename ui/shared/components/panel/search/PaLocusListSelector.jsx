import React, { useEffect, useRef } from 'react'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { useSelector } from 'react-redux'
import { useFormState } from 'react-final-form'
import { getLocusListsWithGenes } from 'redux/selectors'
import { moiToMoiInitials, formatPanelAppItems } from 'shared/utils/panelAppUtils'
import PropTypes from 'prop-types'

const PaLocusListSelector = ({ locus, onChange, color, value, ...props }) => {
  const locusList = useSelector(state => getLocusListsWithGenes(state)[locus.locusListGuid])
  const selectedMOIs = Object.values(useFormState().values?.search?.locus?.selectedMOIs ?? {}) || []
  const prevValue = useRef(value)

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

  useEffect(() => {
    // TODO: A saved search with an additional text input will be overridden here
    // if there are any MOIs selected
    // Need to figure out a way to reconcile both ways of changing state
    if (panelAppItems[color] !== prevValue.current) {
      prevValue.current = panelAppItems[color]
      onChange(panelAppItems[color])
    }
  })

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
