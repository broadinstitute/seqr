import React from 'react'
import { ButtonLink } from 'shared/components/StyledComponents'
import Modal from 'shared/components/modal/Modal'
import { EditHPOBulkForm } from './BulkEditForm'

const MODAL_NAME = 'editIndividualsHpoTerms'

export default () => (
  <Modal
    modalName={MODAL_NAME}
    title="Bulk Edit HPO Terms"
    size="large"
    trigger={<ButtonLink>Edit Individuals</ButtonLink>}
  >
    <EditHPOBulkForm modalName={MODAL_NAME} />
  </Modal>

)

