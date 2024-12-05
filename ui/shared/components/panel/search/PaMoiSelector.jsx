import PropTypes from 'prop-types'
import React, { useCallback, useEffect, useRef } from 'react'
import { useSelector } from 'react-redux'

import { getLocusListsWithGenes } from 'redux/selectors'
import { Multiselect } from 'shared/components/form/Inputs'
import { moiToMoiInitials } from 'shared/utils/panelAppUtils'
import { PANEL_APP_MOI_OPTIONS } from 'shared/utils/constants'

const EMPTY_LIST = []

const PaMoiSelector = ({ locus, onChange, value, ...props }) => {
  const locusList = useSelector(state => getLocusListsWithGenes(state)[locus.locusListGuid])

  const moiInitials = locusList?.items?.reduce((acc, gene) => {
    moiToMoiInitials(gene.pagene?.modeOfInheritance, false).forEach((initial) => {
      acc[initial] = true
    })
    return acc
  }, {}) || {}

  const moiOptions = PANEL_APP_MOI_OPTIONS.map(moi => ({
    ...moi,
    disabled: !moiInitials[moi.value],
  }))

  const prevValue = useRef(value)

  const handleMOIselect = useCallback((selectedMOIs) => {
    if (selectedMOIs !== prevValue) {
      prevValue.current = selectedMOIs
      onChange(selectedMOIs)
    }
  }, [onChange])

  useEffect(() => {
    handleMOIselect(value)
  })

  return (
    <Multiselect
      label={props.label}
      value={value}
      width={props.width}
      inline
      onChange={handleMOIselect}
      placeholder="Showing all MOIs as listed in Panel App"
      disabled={props.disabled}
      options={props.disabled ? EMPTY_LIST : moiOptions}
      color="violet"
    />
  )
}

export default PaMoiSelector

PaMoiSelector.propTypes = {
  locus: PropTypes.object,
  onChange: PropTypes.func,
  value: PropTypes.object,
  label: PropTypes.string,
  width: PropTypes.number,
  disabled: PropTypes.bool,
}
