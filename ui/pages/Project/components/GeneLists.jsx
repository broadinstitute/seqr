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
import { updateLocusLists } from '../reducers'

const ItemContainer = styled.div`
  padding: 2px 0px;
  white-space: nowrap;
`

const LocusListItem = React.memo(({ project, locusList, onSubmit }) => (
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
      content={
        <div>
          <b>{`${locusList.numEntries} Genes`}</b>
          <br />
          <i>{locusList.description}</i>
        </div>
      }
      size="small"
    />
    {project.canEdit && (
      <DeleteButton
        onSubmit={onSubmit}
        size="tiny"
        confirmDialog={
          <div className="content">
            Are you sure you want to remove &nbsp;
            <b>{locusList.name}</b>
            &nbsp; from this project
          </div>
        }
      />
    )}
  </ItemContainer>
))

LocusListItem.propTypes = {
  project: PropTypes.object.isRequired,
  locusList: PropTypes.object.isRequired,
  onSubmit: PropTypes.func.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.locusListGuid],
})

const mapItemDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: values => dispatch(updateLocusLists({ ...values, locusListGuids: [ownProps.locusListGuid] })),
})

const LocusList = connect(mapStateToProps, mapItemDispatchToProps)(LocusListItem)

export const GeneLists = React.memo(({ project }) => project.locusListGuids.map(
  locusListGuid => <LocusList key={locusListGuid} project={project} locusListGuid={locusListGuid} />,
))

GeneLists.propTypes = {
  project: PropTypes.object.isRequired,
}

class AddGeneLists extends React.PureComponent {

  static propTypes = {
    project: PropTypes.object,
    updateLocusLists: PropTypes.func,
    setModalConfirm: PropTypes.func,
    closeModal: PropTypes.func,
  }

  state = { selected: {} }

  constructor(props) {
    super(props)

    this.modalName = `${props.project.projectGuid}-add-gene-list`
  }

  selectList = (updatedSelected) => {
    const { setModalConfirm: dispatchSetModalConfirm } = this.props
    this.setState({ selected: updatedSelected })
    dispatchSetModalConfirm(
      this.modalName,
      Object.values(updatedSelected).some(isSelected => isSelected) ?
        'Gene lists have not been added. Are you sure you want to close?' : null,
    )
  }

  submit = () => {
    const { updateLocusLists: dispatchUpdateLocusLists } = this.props
    const { selected } = this.state
    return dispatchUpdateLocusLists({
      locusListGuids: Object.keys(selected).filter(locusListGuid => selected[locusListGuid]),
    })
  }

  closeModal = () => {
    const { setModalConfirm: dispatchSetModalConfirm, closeModal: dispatchCloseModal } = this.props
    dispatchSetModalConfirm(this.modalName, null)
    dispatchCloseModal(this.modalName)
  }

  render() {
    const { project } = this.props
    const { selected } = this.state
    return (
      <Modal
        title="Add Gene Lists"
        modalName={this.modalName}
        trigger={
          <ButtonLink>
            Add Gene List
            <Icon name="plus" />
          </ButtonLink>
        }
        size="large"
      >
        <LocusListsLoader>
          {`Add an existing Gene List to ${project.name} or `}
          <CreateLocusListButton />
          <LocusListTables
            basicFields
            omitLocusLists={project.locusListGuids}
            selectRows={this.selectList}
            selectedRows={selected}
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

const mapDispatchToProps = { setModalConfirm, closeModal, updateLocusLists }

export const AddGeneListsButton = connect(null, mapDispatchToProps)(AddGeneLists)
