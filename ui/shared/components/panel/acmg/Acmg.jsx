import PropTypes from 'prop-types'

import React, { useState } from 'react'
import AcmgModal from './AcmgModal'

export const Acmg = (props) => {
  const { variant } = props

  const [classification, setClassification] = useState(variant.classification ? variant.classification.classification : 'Unknown')
  const [active, setActive] = useState(false)
  const [criteria, setCriteria] = useState(variant.classification ? variant.classification.criteria : [])

  return (
    <div>
      <AcmgModal classification={classification} setClassification={setClassification} active={active} setActive={setActive} criteria={criteria} setCriteria={setCriteria} variant={variant} />
    </div>
  )
}

Acmg.propTypes = {
  variant: PropTypes.object.isRequired,
}
