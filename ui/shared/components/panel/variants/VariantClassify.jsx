import React from 'react'
import PropTypes from 'prop-types'
import { Button, Label } from 'semantic-ui-react'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { ColoredIcon } from 'shared/components/StyledComponents'
import AcmgModal from '../acmg/AcmgModal'
import { VerticalSpacer } from '../../Spacers'
import PopupWithModal from '../../PopupWithModal'
import { getVariantMainTranscript } from '../../../utils/constants'

const CLINGEN_ALLELE_REGISTRY_URL = 'http://reg.genome.network/allele'
const CLINGEN_VCI_URL = 'https://curation.clinicalgenome.org/select-variant'

class ClinGenAlleleId extends React.PureComponent {

  static propTypes = {
    hgvsc: PropTypes.string,
  }

  state = {
    copied: false,
    alleleId: null,
  };

  constructor(props) {
    super()

    const { hgvsc } = props
    new HttpRequestHelper(CLINGEN_ALLELE_REGISTRY_URL,
      (responseJson) => {
        this.setState({ alleleId: responseJson['@id'].split('/').pop() })
      },
      (e) => {
        this.setState({ alleleId: e.message })
      }).get({ hgvs: hgvsc }, { credentials: 'omit' })
  }

  onCopy = () => {
    this.setState({ copied: true })
  }

  render() {
    const { alleleId, copied } = this.state

    return (
      <CopyToClipboard
        text={alleleId}
        onCopy={this.onCopy}
      >
        <div>
          <span>
            {alleleId}
            &nbsp;
          </span>
          <ColoredIcon name="copy" link />
          {copied && <ColoredIcon name="check circle" color="#00C000" />}
        </div>
      </CopyToClipboard>
    )
  }

}

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
            <div>
              <a href={CLINGEN_VCI_URL} target="_blank" rel="noreferrer">
                In ClinGen VCI
              </a>
              <br />
              <ClinGenAlleleId hgvsc={hgvsc} />
              <VerticalSpacer height={10} />
            </div>
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
