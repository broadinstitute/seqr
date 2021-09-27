import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { Button, Icon, Modal } from 'semantic-ui-react'
import AcmgScoreCriteria from './AcmgScoreCriteria'
import AcmgCriteria from './AcmgCriteria'

const getButonBackgroundColor = (classification) => {
  const categoryColors = {
    Unknown: 'grey',
    Benign: 'blue',
    'Likely Benign': 'blue',
    Pathogenic: 'orange',
    'Likely Pathogenic': 'orange',
    Uncertain: 'yellow',
  }

  return categoryColors[classification]
}

const AcmgModal = (props) => {
  const { variant } = props

  const [acmgClassification, setAcmgClassification] = useState(variant.acmgClassification ? variant.acmgClassification.classify : 'Unknown')
  const [active, setActive] = useState(false)
  const [criteria, setCriteria] = useState(variant.acmgClassification ? variant.acmgClassification.criteria : [])

  const buttonBackgroundColor = getButonBackgroundColor(acmgClassification)

  return (
    <div>
      <Button color={buttonBackgroundColor} tabIndex={0} onClick={() => { setActive(true) }}>Classify {acmgClassification}</Button>
      <Modal open={active} dimmer="blurring" size="fullscreen" >
        <Icon name="close" onClick={() => { setActive(false) }} />

        <Modal.Header>ACMG Calculation</Modal.Header>

        <Modal.Content>
          <AcmgScoreCriteria classify={acmgClassification} criteria={criteria} />
          <br />
          <AcmgCriteria
            criteria={criteria}
            setCriteria={setCriteria}
            acmgClassification={acmgClassification}
            setAcmgClassification={setAcmgClassification}
            setActive={setActive}
            variant={variant}
          />
        </Modal.Content>
      </Modal>
    </div>
  )
}

AcmgModal.propTypes = {
  variant: PropTypes.object.isRequired,
}

export default AcmgModal
