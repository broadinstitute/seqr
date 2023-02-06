import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import { getClinGeneAlleleIdIsLoading, getClinGenAlleleIdByHgvsc } from 'redux/selectors'
import { loadClinGeneAlleleId } from 'redux/rootReducer'
import DataLoader from '../../DataLoader'
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
    const clinGenAlleleId = clinGenAlleleIdByHgvsc[hgvsc]
    const { copied } = this.state
    return (
      <DataLoader contentId={hgvsc} load={load} loading={loading} content={clinGenAlleleId}>
        <span>
          {(clinGenAlleleId || {})['@id']}
          &nbsp;
        </span>
        <CopyToClipboard
          text={(clinGenAlleleId || {})['@id']}
          onCopy={this.onCopy}
        >
          <Icon name="copy" />
        </CopyToClipboard>
        {copied ? <span>&nbsp;Copied.</span> : null}
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

const ClinGenVciLink = (props) => {
  const { variant } = props

  return (
    <div>
      <a href="https://curation.clinicalgenome.org/select-variant" target="_blank" rel="noreferrer">
        In ClinGen VCI
      </a>
      <br />
      <ClinGenAlleleId variant={variant} />
    </div>
  )
}

ClinGenVciLink.propTypes = {
  variant: PropTypes.object.isRequired,
}

export default ClinGenVciLink
