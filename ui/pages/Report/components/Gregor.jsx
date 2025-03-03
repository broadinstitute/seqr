import React from 'react'

import { validators } from 'shared/components/form/FormHelpers'
import { ButtonRadioGroup, InlineToggle } from 'shared/components/form/Inputs'
import SubmitFormPage from 'shared/components/page/SubmitFormPage'
import { CONSENT_CODES } from 'shared/utils/constants'

const FIELDS = [
  {
    name: 'overrideValidation',
    label: 'Upload with Validation Errors',
    component: InlineToggle,
    asFormInput: true,
    fullHeight: true,
    inline: false,
  },
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

const Gregor = () => (
  <SubmitFormPage
    fields={FIELDS}
    url="/api/report/gregor"
    header="Validate and Upload GREGoR Reports"
  />
)

export default Gregor
