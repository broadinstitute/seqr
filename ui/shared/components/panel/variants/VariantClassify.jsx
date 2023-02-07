import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Button, Icon, Label } from 'semantic-ui-react'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import { getClinGeneAlleleIdIsLoading, getClinGenAlleleIdByHgvsc } from 'redux/selectors'
import { loadClinGeneAlleleId } from 'redux/rootReducer'
import AcmgModal from '../acmg/AcmgModal'
import DataLoader from '../../DataLoader'
import { VerticalSpacer } from '../../Spacers'
import PopupWithModal from '../../PopupWithModal'
import { getVariantMainTranscript } from '../../../utils/constants'

class BaseClinGenAlleleId extends React.PureComponent {

  static propTypes = {
    clinGenAlleleIdByHgvsc: PropTypes.object,
    variant: PropTypes.object,
    load: PropTypes.func,
    loading: PropTypes.bool,
  }

  state = {
    copied: false,
  };

  onCopy = () => {
    this.setState({ copied: true })
  }

  render() {
    const { clinGenAlleleIdByHgvsc, variant, load, loading } = this.props
    const { hgvsc } = getVariantMainTranscript(variant)
    const { alleleId } = clinGenAlleleIdByHgvsc[hgvsc] || {}
    const { copied } = this.state
    return (
      <DataLoader contentId={hgvsc} load={load} loading={loading} content={alleleId}>
        <CopyToClipboard
          text={alleleId}
          onCopy={this.onCopy}
        >
          <div>
            <span>
              {alleleId}
              &nbsp;
            </span>
            <Icon name="copy" link />
          </div>
        </CopyToClipboard>
        {copied ? <Label floating>Copied.</Label> : null}
      </DataLoader>
    )
  }

}

const mapStateToProps = state => ({
  loading: getClinGeneAlleleIdIsLoading(state),
  clinGenAlleleIdByHgvsc: getClinGenAlleleIdByHgvsc(state),
})

const mapDispatchToProps = {
  load: loadClinGeneAlleleId,
}

const ClinGenAlleleId = connect(mapStateToProps, mapDispatchToProps)(BaseClinGenAlleleId)

const VariantClassify = (props) => {
  const { variant, familyGuid } = props
  const { classify } = variant.acmgClassification || {}

  return (
    <PopupWithModal
      content={
        <div>
          <a href="https://curation.clinicalgenome.org/select-variant" target="_blank" rel="noreferrer">
            - In ClinGen VCI
          </a>
          <br />
          <ClinGenAlleleId variant={variant} />
          <VerticalSpacer height={10} />
          <AcmgModal variant={variant} familyGuid={familyGuid} />
        </div>
      }
      trigger={<Button as={Label} content={`Classify ${classify || ''}`} horizontal basic={!classify} size="small" />}
      hoverable
    />
  )
}

VariantClassify.propTypes = {
  variant: PropTypes.object.isRequired,
  familyGuid: PropTypes.string,
}

export default VariantClassify
