import React from 'react'
import { ButtonLink } from 'shared/components/StyledComponents'
import Modal from 'shared/components/modal/Modal'
import { EditIndividualMetadataBulkForm } from './BulkEditForm'

const MODAL_NAME = 'editIndividualsMetadata'

export default React.memo(() => (
  <Modal
    modalName={MODAL_NAME}
    title="Bulk Edit Individual Metadata"
    size="large"
    trigger={<ButtonLink>Bulk Edit Metadata</ButtonLink>}
  >
    <EditIndividualMetadataBulkForm modalName={MODAL_NAME} />
  </Modal>

))
