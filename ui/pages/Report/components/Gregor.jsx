import React from 'react'
import { Header } from 'semantic-ui-react'

import { validators } from 'shared/components/form/FormHelpers'
import { ButtonRadioGroup } from 'shared/components/form/Inputs'
import UploadFormPage from 'shared/components/page/UploadFormPage'
import { CONSENT_CODES } from 'shared/utils/constants'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

const FIELDS = [

  {
    name: 'deliveryPath',
    label: 'AnVIL Delivery Bucket Path',
    placeholder: 'gs:// path',
    validate: validators.required,
  },
  {
    name: 'consentCode',
    label: 'Consent Code',
    component: ButtonRadioGroup,
    options: CONSENT_CODES.map(code => ({ value: code, text: code })),
    validate: validators.required,
  },
]

class Gregor extends React.PureComponent {

  state = { uploadStats: {} }

  onSubmit = values => new HttpRequestHelper('/api/report/gregor',
    (uploadStats) => {
      this.setState({ uploadStats })
    }, (error) => {
      if (error?.body) {
        this.setState({ uploadStats: error.body })
      }
      return Promise.reject(error)
    }).post(values)

  render() {
    const { uploadStats } = this.state
    return (
      <div>
        <Header size="medium" textAlign="center" content="Validate and Upload GREGoR Reports" />
        <UploadFormPage fields={FIELDS} uploadStats={uploadStats} onSubmit={this.onSubmit} />
      </div>
    )
  }

}

export default Gregor
