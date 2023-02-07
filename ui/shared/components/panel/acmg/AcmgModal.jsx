import React from 'react'
import PropTypes from 'prop-types'
import { Loader } from 'semantic-ui-react'
import Modal from '../../modal/Modal'
import { ButtonLink } from '../../StyledComponents'

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
        <ButtonLink color={buttonBackgroundColor} content={`- In seqr ${classify || ''}`} />
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
