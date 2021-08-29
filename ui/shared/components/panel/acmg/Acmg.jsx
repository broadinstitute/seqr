import PropTypes from 'prop-types'

import React, { useState } from 'react'
import AcmgModal from './AcmgModal'
import { updateAcmgCriteriaForFileDownload } from '../../buttons/ExportTableButton'

export const Acmg = (props) => {
  const [classification, setClassification] = useState('Unknown')
  const [active, setActive] = useState(false)
  const [criteria, setCriteria] = useState([])

  const { variantId } = props
  updateAcmgCriteriaForFileDownload(variantId, classification, criteria)

  return (
    <div>
      <AcmgModal classification={classification} setClassification={setClassification} active={active} setActive={setActive} criteria={criteria} setCriteria={setCriteria} />
    </div>
  )
}

Acmg.propTypes = {
  variantId: PropTypes.string,
}
