import React from 'react'
import PropTypes from 'prop-types'
import { Icon, Modal } from 'semantic-ui-react'
import AcmgScoreCriteria from './AcmgScoreCriteria'
import AcmgCriteria from './AcmgCriteria'

const getButonBackgroundColor = (classification) => {
  const categoryColors = {
    Unknown: '#BABABA',
    Benign: '#5E6F9E',
    'Likely Benign': '#5E6F9E',
    Pathogenic: '#E6573D',
    'Likely Pathogenic': '#E6573D',
    Uncertain: '#FAB470',
  }

  return categoryColors[classification]
}

const AcmgModal = (props) => {
  const { classification, setClassification, active, setActive, criteria, setCriteria, variant } = props
  const buttonBackgroundColor = getButonBackgroundColor(classification)

  return (
    <div>
      <div className="ui labels">
        <a className="ui label large" role="button" style={{ backgroundColor: buttonBackgroundColor, color: 'white' }} tabIndex={0} onClick={() => { setActive(true) }}>Classify<div className="detail">{classification}</div></a>
        <Modal open={active} dimmer="blurring" size="fullscreen" >
          <Icon name="close" onClick={() => { setActive(false) }} />

          <Modal.Header>ACMG Calculation</Modal.Header>

          <Modal.Content>
            <AcmgScoreCriteria classification={classification} criteria={criteria} />
            <br />
            <AcmgCriteria
              criteria={criteria}
              setCriteria={setCriteria}
              classification={classification}
              setClassification={setClassification}
              setActive={setActive}
              variant={variant}
            />
          </Modal.Content>
        </Modal>
      </div>
    </div>
  )
}

AcmgModal.propTypes = {
  classification: PropTypes.string.isRequired,
  setClassification: PropTypes.func.isRequired,
  active: PropTypes.bool.isRequired,
  setActive: PropTypes.func.isRequired,
  criteria: PropTypes.array.isRequired,
  setCriteria: PropTypes.func.isRequired,
  variant: PropTypes.object.isRequired,
}

export default AcmgModal
