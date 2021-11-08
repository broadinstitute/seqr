import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { Button, Icon, Modal } from 'semantic-ui-react'
import AcmgScoreCriteria from './AcmgScoreCriteria'
import AcmgCriteria from './AcmgCriteria'
import { VerticalSpacer } from '../../Spacers'

const getButtonBackgroundColor = (classification) => {
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

  const buttonBackgroundColor = getButtonBackgroundColor(acmgClassification)

  return (
    <div>
      <VerticalSpacer height={12} />
      <Button
        color={buttonBackgroundColor}
        tabIndex={0}
        /* eslint-disable react-perf/jsx-no-new-function-as-prop */
        onClick={() => { setActive(true) }}
      >
        {/* eslint-disable react/jsx-one-expression-per-line */}
        Classify {acmgClassification}
      </Button>
      <Modal open={active} dimmer="blurring" size="fullscreen">
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
