import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { Icon, Modal } from 'semantic-ui-react'
import AcmgScoreCriteria from './AcmgScoreCriteria'
import AcmgCriteria from './AcmgCriteria'

const getPathOneResult = (acmgCalculationValue) => {
  if (acmgCalculationValue.PVS >= 1) {
    if (acmgCalculationValue.PS >= 1 || acmgCalculationValue.PM >= 2 || acmgCalculationValue.PP >= 2 || (acmgCalculationValue.PM >= 1 && acmgCalculationValue.PP >= 1)) {
      return 'Path'
    }

    return 'No'
  }
  return 'No'
}

const getPathTwoResult = (acmgCalculationValue) => {
  if (acmgCalculationValue.PVS >= 2 || acmgCalculationValue.PS >= 2) {
    return 'Path'
  }
  return 'No'
}

const getPathThreeResult = (acmgCalculationValue) => {
  if (acmgCalculationValue.PS >= 1) {
    if (acmgCalculationValue.PM >= 3 || (acmgCalculationValue.PM >= 2 && acmgCalculationValue.PP >= 2) || (acmgCalculationValue.PM >= 1 && acmgCalculationValue.PP >= 4)) {
      return 'Path'
    }
    return 'No'
  }
  return 'No'
}

const isPathogenic = (acmgCalculationValue) => {
  if (getPathOneResult(acmgCalculationValue) === 'Path' || getPathTwoResult(acmgCalculationValue) === 'Path' || getPathThreeResult(acmgCalculationValue) === 'Path') {
    return 'Yes'
  }
  return 'No'
}

const isLikelyPath = (acmgCalculationValue) => {
  if (
    (acmgCalculationValue.PVS === 1 && acmgCalculationValue.PM === 1) ||
    (acmgCalculationValue.PS === 1 && acmgCalculationValue.PM === 1) ||
    (acmgCalculationValue.PS === 1 && acmgCalculationValue.PM === 2) ||
    (acmgCalculationValue.PS === 1 && acmgCalculationValue.PP >= 2) ||
    (acmgCalculationValue.PM >= 3) ||
    (acmgCalculationValue.PM === 2 && acmgCalculationValue.PP >= 2) ||
    (acmgCalculationValue.PM === 1 && acmgCalculationValue.PP >= 4)
  ) {
    return 'Yes'
  }
  return 'No'
}

const isLikelyBenign = (acmgCalculationValue) => {
  if (acmgCalculationValue.BP >= 2 || (acmgCalculationValue.BS >= 1 && acmgCalculationValue.BP >= 1)) {
    return 'Yes'
  }
  return 'No'
}

const isBenign = (acmgCalculationValue) => {
  if (acmgCalculationValue.BA >= 1 || acmgCalculationValue.BS >= 2) {
    return 'Yes'
  }
  return 'No'
}

const getScore = (acmgCalculationValue) => {
  if (
    acmgCalculationValue.PVS === 0 &&
    acmgCalculationValue.PS === 0 &&
    acmgCalculationValue.PM === 0 &&
    acmgCalculationValue.PP === 0 &&
    acmgCalculationValue.BA === 0 &&
    acmgCalculationValue.BS === 0 &&
    acmgCalculationValue.BP === 0
  ) {
    return 'Unknown'
  } else if (
    isPathogenic(acmgCalculationValue) === 'No' &&
    isLikelyPath(acmgCalculationValue) === 'No' &&
    isLikelyBenign(acmgCalculationValue) === 'No' &&
    isBenign(acmgCalculationValue) === 'No'
  ) {
    return 'Uncertain significance'
  } else if (
    (isPathogenic(acmgCalculationValue) === 'Yes' || isLikelyPath(acmgCalculationValue) === 'Yes') &&
    (isLikelyBenign(acmgCalculationValue) === 'Yes' || isBenign(acmgCalculationValue) === 'Yes')
  ) {
    return 'Conflicting'
  } else if (isPathogenic(acmgCalculationValue) === 'Yes') {
    return 'Pathogenic'
  } else if (isPathogenic(acmgCalculationValue) === 'No' && isLikelyPath(acmgCalculationValue) === 'Yes') {
    return 'Likely pathogenic'
  } else if (isLikelyBenign(acmgCalculationValue) === 'Yes' && isBenign(acmgCalculationValue) === 'No') {
    return 'Likely benign'
  } else if (isBenign(acmgCalculationValue) === 'Yes') {
    return 'Benign'
  }
  return 'Unknown'
}

const getButonBackgroundColor = (score) => {
  const categoryColors = {
    Unknown: '#BABABA',
    Benign: '#5E6F9E',
    'Likely benign': '#5E6F9E',
    Pathogenic: '#E6573D',
    'Likely pathogenic': '#E6573D',
    'Uncertain significance': '#FAB470',
  }

  return categoryColors[score]
}

const AcmgModal = (props) => {
  const { score, setScore, active, setActive, criteria, setCriteria } = props

  const [acmgCalculationValue, setAcmgCalculationValue] = useState({
    PVS: 0,
    PS: 0,
    PM: 0,
    PP: 0,
    BA: 0,
    BS: 0,
    BP: 0,
  })

  const buttonBackgroundColor = getButonBackgroundColor(score)

  return (
    <div>
      <div className="ui labels">
        <a className="ui label large" role="button" style={{ backgroundColor: buttonBackgroundColor, color: 'white' }} tabIndex={0} onClick={() => { setActive(true) }}>Classify<div className="detail">{score}</div></a>
        <Modal open={active} dimmer="blurring" size="fullscreen" >
          <Icon name="close" onClick={() => { setActive(false) }} />

          <Modal.Header>ACMG Calculation</Modal.Header>

          <Modal.Content>
            <AcmgScoreCriteria score={score} criteria={criteria} />
            <br />
            <AcmgCriteria
              criteria={criteria}
              setCriteria={setCriteria}
              acmgCalculationValue={acmgCalculationValue}
              setAcmgCalculationValue={setAcmgCalculationValue}
              getScore={getScore}
              setScore={setScore}
              setActive={setActive}
            />
          </Modal.Content>
        </Modal>
      </div>
    </div>
  )
}

AcmgModal.propTypes = {
  score: PropTypes.string.isRequired,
  setScore: PropTypes.func.isRequired,
  active: PropTypes.bool.isRequired,
  setActive: PropTypes.func.isRequired,
  criteria: PropTypes.array.isRequired,
  setCriteria: PropTypes.func.isRequired,
}

export default AcmgModal
