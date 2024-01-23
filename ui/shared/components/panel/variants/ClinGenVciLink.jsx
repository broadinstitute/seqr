import React from 'react'
import PropTypes from 'prop-types'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import CopyToClipboardButton from 'shared/components/buttons/CopyToClipboardButton'
import DataLoader from 'shared/components/DataLoader'

const CLINGEN_ALLELE_REGISTRY_URL = 'https://reg.genome.network/allele'
const CLINGEN_VCI_URL = 'https://curation.clinicalgenome.org/select-variant'

class ClinGenVciLink extends React.PureComponent {

  static propTypes = {
    hgvsc: PropTypes.string.isRequired,
  }

  state = {
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

  render() {
    const { hgvsc } = this.props
    const { alleleId, loading, error } = this.state

    return (
      <DataLoader contentId={hgvsc} content={alleleId || error} loading={loading} load={this.load}>
        <a href={CLINGEN_VCI_URL} target="_blank" rel="noreferrer">In ClinGen VCI</a>
        <br />
        {error || (alleleId && <CopyToClipboardButton text={alleleId} />)}
      </DataLoader>
    )
  }

}

export default ClinGenVciLink
