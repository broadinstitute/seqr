import React from 'react'
import PropTypes from 'prop-types'
import { Button, Loader } from 'semantic-ui-react'
import Modal from '../../modal/Modal'
import { VerticalSpacer } from '../../Spacers'

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
  const { variant } = props
  const modalName = `acmg-${variant.variantGuid}`

  const { classify } = variant.acmgClassification || {}
  const buttonBackgroundColor = getButtonBackgroundColor(classify)

  return (
    <div>
      <VerticalSpacer height={12} />
      <Modal
        title="ACMG Calculation"
        size="fullscreen"
        modalName={modalName}
        trigger={
          <Button color={buttonBackgroundColor} content={`Classify ${classify || ''}`} compact size="mini" />
        }
      >
        <React.Suspense fallback={<Loader />}>
          <AcmgCriteria modalName={modalName} variant={variant} />
        </React.Suspense>
      </Modal>
    </div>
  )
}

AcmgModal.propTypes = {
  variant: PropTypes.object.isRequired,
}

export default AcmgModal
