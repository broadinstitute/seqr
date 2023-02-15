import React from 'react'
import PropTypes from 'prop-types'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { ColoredIcon } from 'shared/components/StyledComponents'
import DataLoader from 'shared/components/DataLoader'

const CLINGEN_ALLELE_REGISTRY_URL = 'https://reg.genome.network/allele'
const CLINGEN_VCI_URL = 'https://curation.clinicalgenome.org/select-variant'

class ClinGenVciLink extends React.PureComponent {

  static propTypes = {
    hgvsc: PropTypes.string.isRequired,
  }

  state = {
    copied: false,
    loading: false,
    alleleId: null,
    error: '',
  };

  load = (hgvsc) => {
    this.setState({ loading: true })
    new HttpRequestHelper(CLINGEN_ALLELE_REGISTRY_URL,
      (responseJson) => {
        this.setState({ alleleId: responseJson['@id'].split('/').pop(), loading: false })
      },
      (e) => {
        this.setState({ error: e.message, loading: false })
      }).get({ hgvs: hgvsc }, { credentials: 'omit' })
  }

  onCopy = () => {
    this.setState({ copied: true })
  }

  render() {
    const { hgvsc } = this.props
    const { alleleId, copied, loading, error } = this.state

    return (
      <DataLoader contentId={hgvsc} content={alleleId || error} loading={loading} load={this.load}>
        <a href={CLINGEN_VCI_URL} target="_blank" rel="noreferrer">In ClinGen VCI</a>
        <br />
        {error || (
          <CopyToClipboard
            text={alleleId}
            onCopy={this.onCopy}
          >
            <div>
              {alleleId}
              &nbsp;
              <ColoredIcon name="copy" link />
              {copied && <ColoredIcon name="check circle" color="green" />}
            </div>
          </CopyToClipboard>
        )}
      </DataLoader>
    )
  }

}

export default ClinGenVciLink
