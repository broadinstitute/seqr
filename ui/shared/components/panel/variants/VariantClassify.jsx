import React from 'react'
import styled from 'styled-components'
import PropTypes from 'prop-types'
import { Button, Label, Loader } from 'semantic-ui-react'
import AcmgModal from '../acmg/AcmgModal'
import PopupWithModal from '../../PopupWithModal'
import { getVariantMainTranscript } from '../../../utils/constants'

const ClinGenVciLink = React.lazy(() => import('./ClinGenVciLink'))

const LoaderContainer = styled.div`
  min-height: 3em;
`

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

const VariantClassify = React.memo(({ variant, familyGuid }) => {
  const { hgvsc } = getVariantMainTranscript(variant)
  const { classify } = variant.acmgClassification || {}
  const buttonBackgroundColor = getButtonBackgroundColor(classify)

  return (
    <PopupWithModal
      content={
        <div>
          {hgvsc && (
            <LoaderContainer>
              <React.Suspense fallback={<Loader />}>
                <ClinGenVciLink hgvsc={hgvsc} />
              </React.Suspense>
            </LoaderContainer>
          )}
          <AcmgModal variant={variant} familyGuid={familyGuid} />
        </div>
      }
      trigger={
        <Button as={Label} color={buttonBackgroundColor} horizontal basic={!classify} size="small">
          {`Classify ${classify || ''}`}
        </Button>
      }
      on="click"
      hoverable
    />
  )
})

VariantClassify.propTypes = {
  variant: PropTypes.object.isRequired,
  familyGuid: PropTypes.string,
}

export default VariantClassify
