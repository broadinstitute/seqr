import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon, Button, Divider } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getLocusListsByGuid } from 'redux/selectors'
import { setModalConfirm, closeModal } from 'redux/utils/modalReducer'
import { LocusListsLoader } from 'shared/components/LocusListLoader'
import LocusListDetailPanel from 'shared/components/panel/genes/LocusListDetail'
import LocusListTables from 'shared/components/table/LocusListTables'
import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import DispatchRequestButton from 'shared/components/buttons/DispatchRequestButton'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import Modal from 'shared/components/modal/Modal'
import { HelpIcon, ButtonLink } from 'shared/components/StyledComponents'
import {
  LOCUS_LIST_IS_PUBLIC_FIELD_NAME, LOCUS_LIST_LAST_MODIFIED_FIELD_NAME, LOCUS_LIST_CURATOR_FIELD_NAME,
} from 'shared/utils/constants'
import { updateLocusLists } from '../reducers'

const ItemContainer = styled.div`
  padding: 2px 0px;
  white-space: nowrap;
`

const OMIT_LOCUS_LIST_FIELDS = [
  LOCUS_LIST_IS_PUBLIC_FIELD_NAME,
  LOCUS_LIST_LAST_MODIFIED_FIELD_NAME,
  LOCUS_LIST_CURATOR_FIELD_NAME,
]

const LocusListItem = ({ project, locusList, updateLocusLists: onSubmit }) => {
  const submitValues = { locusListGuids: [locusList.locusListGuid] }
  return (
    <ItemContainer key={locusList.locusListGuid}>
      <Modal
        title={`${locusList.name} Gene List`}
        modalName={`${project.projectGuid}-${locusList.name}-genes`}
        trigger={<ButtonLink>{locusList.name}</ButtonLink>}
        size="large"
      >
        <LocusListDetailPanel locusListGuid={locusList.locusListGuid} />
      </Modal>
      <Popup
        position="right center"
        trigger={<HelpIcon />}
        content={<div><b>{locusList.numEntries} Genes</b><br /><i>{locusList.description}</i></div>}
        size="small"
      />
      {project.canEdit &&
        <DeleteButton
          initialValues={submitValues}
          onSubmit={onSubmit}
          confirmDialog={
            <div className="content">
              Are you sure you want to remove <b>{locusList.name}</b> from this project
            </div>
          }
        />
      }
    </ItemContainer>
  )
}

LocusListItem.propTypes = {
  project: PropTypes.object.isRequired,
  locusList: PropTypes.object.isRequired,
  updateLocusLists: PropTypes.func.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.locusListGuid],
})

const mapDispatchToProps = { setModalConfirm, closeModal, updateLocusLists }

const LocusList = connect(mapStateToProps, mapDispatchToProps)(LocusListItem)

export const GeneLists = ({ project }) =>
  project.locusListGuids.map(locusListGuid =>
    <LocusList
      key={locusListGuid}
      project={project}
      locusListGuid={locusListGuid}
    />,
  )

class AddGeneLists extends React.PureComponent {

  static propTypes = {
    project: PropTypes.object,
    updateLocusLists: PropTypes.func,
    setModalConfirm: PropTypes.func,
    closeModal: PropTypes.func,
  }

  constructor(props) {
    super(props)

    this.state = {
      selected: {},
    }
    this.modalName = `${props.project.projectGuid}-add-gene-list`
  }

  selectList = (updatedSelected) => {
    this.setState({ selected: updatedSelected })
    this.props.setModalConfirm(
      this.modalName,
      Object.values(updatedSelected).some(isSelected => isSelected) ?
        'Gene lists have not been added. Are you sure you want to close?' : null,
    )
  }

  submit = () => {
    return this.props.updateLocusLists({
      locusListGuids: Object.keys(this.state.selected).filter(locusListGuid => this.state.selected[locusListGuid]),
    })
  }

  closeModal = () => {
    this.props.setModalConfirm(this.modalName, null)
    this.props.closeModal(this.modalName)
  }

  render() {
    return (
      <Modal
        title="Add Gene Lists"
        modalName={this.modalName}
        trigger={<ButtonLink>Add Gene List <Icon name="plus" /></ButtonLink>}
        size="large"
      >
        <LocusListsLoader>
          Add an existing Gene List to {this.props.project.name} or <CreateLocusListButton />
          <LocusListTables
            isEditable={false}
            showLinks={false}
            omitFields={OMIT_LOCUS_LIST_FIELDS}
            omitLocusLists={this.props.project.locusListGuids}
            selectRows={this.selectList}
            selectedRows={this.state.selected}
          />
          <Divider />
          <DispatchRequestButton onSubmit={this.submit} onSuccess={this.closeModal}>
            <Button content="Submit" primary />
          </DispatchRequestButton>
        </LocusListsLoader>
      </Modal>
    )
  }
}

export const AddGeneListsButton = connect(null, mapDispatchToProps)(AddGeneLists)
