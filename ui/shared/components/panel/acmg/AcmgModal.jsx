import React from 'react'
import PropTypes from 'prop-types'
import { Button, Label, Loader } from 'semantic-ui-react'
import Modal from '../../modal/Modal'

const AcmgCriteria = React.lazy(() => import('./AcmgCriteria'))

const getButtonBackgroundColor = (classification) => {
  const categoryColors = {
    Unknown: 'grey',
    Benign: 'blue',
    'Likely Benign': 'blue',
    Pathogenic: 'orange',
    'Likely Pathogenic': 'orange',
    Uncertain: 'yellow',
  }
  return categoryColors[classification] || 'grey'
}

const AcmgModal = (props) => {
  const { variant, familyGuid } = props
  const modalName = `acmg-${variant.variantGuid}-${familyGuid}`

  const { classify } = variant.acmgClassification || {}
  const buttonBackgroundColor = getButtonBackgroundColor(classify)

  return (
    <Modal
      title="ACMG Calculation"
      size="fullscreen"
      modalName={modalName}
      trigger={
        <Button as={Label} color={buttonBackgroundColor} content={`Classify ${classify || ''}`} horizontal basic={!classify} size="small" />
      }
    >
      <React.Suspense fallback={<Loader />}>
        <AcmgCriteria modalName={modalName} variant={variant} />
      </React.Suspense>
    </Modal>
  )
}

AcmgModal.propTypes = {
  variant: PropTypes.object.isRequired,
  familyGuid: PropTypes.string.isRequired,
}

export default AcmgModal
