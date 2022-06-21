import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getLocusListsByGuid } from 'redux/selectors'
import { LocusListsLoader } from 'shared/components/LocusListLoader'
import LocusListDetailPanel from 'shared/components/panel/genes/LocusListDetail'
import LocusListTables from 'shared/components/table/LocusListTables'
import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import { validators } from 'shared/components/form/FormHelpers'
import Modal from 'shared/components/modal/Modal'
import { HelpIcon, ButtonLink } from 'shared/components/StyledComponents'
import { updateLocusLists } from '../reducers'

const ItemContainer = styled.div`
  padding: 2px 0px;
  white-space: nowrap;
  
  button:first-child {
    max-width: calc(100% - 40px);
    text-align: left;
    white-space: normal !important;
  }
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

export class GeneLists extends React.PureComponent {

  static propTypes = {
    project: PropTypes.object.isRequired,
  }

  state = { showAll: false }

  show = () => {
    this.setState({ showAll: true })
  }

  render() {
    const { project } = this.props
    const { showAll } = this.state

    const locusListGuids = project.locusListGuids || []
    const locusListsToShow = showAll ? locusListGuids : locusListGuids.slice(0, 20)

    return [
      ...locusListsToShow.map(
        locusListGuid => <LocusList key={locusListGuid} project={project} locusListGuid={locusListGuid} />,
      ),
      locusListsToShow.length < locusListGuids.length ?
        <ButtonLink key="show" padding="15px 0 0 0" color="grey" onClick={this.show}>Show More...</ButtonLink> :
        null,
    ]
  }

}

const LOCUS_LIST_FIELDS = [{
  name: 'locusListGuids',
  component: LocusListTables,
  basicFields: true,
  maxHeight: '500px',
  validate: validators.requiredList,
  parse: value => Object.keys(value || {}).filter(locusListGuid => value[locusListGuid]),
  format: value => (value || []).reduce((acc, locusListGuid) => ({ ...acc, [locusListGuid]: true }), {}),
}]

const LocustListsContainer = ({ project, children }) => (
  <LocusListsLoader>
    {`Add an existing Gene List to ${project.name} or `}
    <CreateLocusListButton />
    {children}
  </LocusListsLoader>
)

LocustListsContainer.propTypes = {
  project: PropTypes.object,
  children: PropTypes.node,
}

const AddGeneLists = React.memo(({ project, onSubmit }) => (
  <UpdateButton
    modalTitle="Add Gene Lists"
    modalId={`add-gene-list-${project.projectGuid}`}
    formMetaId={project.projectGuid}
    modalSize="large"
    buttonText="Add Gene List"
    editIconName="plus"
    formContainer={<LocustListsContainer project={project} />}
    onSubmit={onSubmit}
    formFields={LOCUS_LIST_FIELDS}
    showErrorPanel
  />
))

AddGeneLists.propTypes = {
  project: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = { onSubmit: updateLocusLists }

export const AddGeneListsButton = connect(null, mapDispatchToProps)(AddGeneLists)
