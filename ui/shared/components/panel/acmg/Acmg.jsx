import PropTypes from 'prop-types'

import React, { useState } from 'react'
import AcmgModal from './AcmgModal'
import { updateAcmgCriteriaForFileDownload } from '../../buttons/ExportTableButton'

export const Acmg = (props) => {
  const [score, setScore] = useState('Unknown')
  const [active, setActive] = useState(false)
  const [criteria, setCriteria] = useState([])

  const { variantId } = props
  updateAcmgCriteriaForFileDownload(variantId, score, criteria)

  return (
    <div>
      <AcmgModal score={score} setScore={setScore} active={active} setActive={setActive} criteria={criteria} setCriteria={setCriteria} />
    </div>
  )
}

Acmg.propTypes = {
  variantId: PropTypes.string,
}
