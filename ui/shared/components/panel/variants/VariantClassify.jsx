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

const ClinGenAlleleId = ({ alleleId, copied, onCopy }) => (
  <CopyToClipboard
    text={alleleId}
    onCopy={onCopy}
  >
    <div>
      <span>
        {alleleId}
        &nbsp;
      </span>
      {copied ? <ColoredIcon name="check circle" color="#00C000" /> : <ColoredIcon name="copy" link />}
    </div>
  </CopyToClipboard>
)

ClinGenAlleleId.propTypes = {
  alleleId: PropTypes.string,
  copied: PropTypes.bool,
  onCopy: PropTypes.func,
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

class VariantClassify extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object.isRequired,
    familyGuid: PropTypes.string,
  }

  state = {
    copied: false,
    alleleId: null,
  };

  onOpenPopup = hgvsc => () => {
    const { alleleId } = this.state
    this.setState({ copied: false })
    if (!alleleId) {
      new HttpRequestHelper(CLINGEN_ALLELE_REGISTRY_URL,
        (responseJson) => {
          this.setState({ alleleId: responseJson['@id'].split('/').pop() })
        },
        (e) => {
          this.setState({ alleleId: e.message })
        }).get({ hgvs: hgvsc }, 'omit')
    }
  }

  onCopy = () => {
    this.setState({ copied: true })
  }

  render() {
    const { variant, familyGuid } = this.props
    const { copied, alleleId } = this.state
    const { hgvsc } = getVariantMainTranscript(variant)
    const { classify } = variant.acmgClassification || {}
    const buttonBackgroundColor = getButtonBackgroundColor(classify)

    return (
      <PopupWithModal
        onOpen={this.onOpenPopup(hgvsc)}
        header={classify}
        content={
          <div>
            {alleleId && (
              <div>
                <a href={CLINGEN_VCI_URL} target="_blank" rel="noreferrer">
                  In ClinGen VCI
                </a>
                <br />
                <ClinGenAlleleId alleleId={alleleId} onCopy={this.onCopy} copied={copied} />
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
        hoverable
      />
    )
  }

}

export default VariantClassify
