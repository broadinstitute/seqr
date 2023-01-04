import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Dimmer, Loader, Popup } from 'semantic-ui-react'
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
import { loadProjectLocusLists, updateLocusLists } from '../reducers'
import { getCurrentProject, getProjectLocusListsIsLoading } from '../selectors'

const ItemContainer = styled.div`
  padding: 2px 0px;
  white-space: nowrap;
  
  button:first-child {
    max-width: calc(100% - 40px);
    text-align: left;
    white-space: normal !important;
  }
`

const LocusListItem = React.memo(({ projectGuid, canEdit, locusList, onSubmit }) => (
  <ItemContainer key={locusList.locusListGuid}>
    <Modal
      title={`${locusList.name} Gene List`}
      modalName={`${projectGuid}-${locusList.name}-genes`}
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
    {canEdit && (
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
  projectGuid: PropTypes.string.isRequired,
  locusList: PropTypes.object.isRequired,
  canEdit: PropTypes.bool,
  onSubmit: PropTypes.func.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.locusListGuid],
})

const mapItemDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: values => dispatch(updateLocusLists({ ...values, locusListGuids: [ownProps.locusListGuid] })),
})

const LocusList = connect(mapStateToProps, mapItemDispatchToProps)(LocusListItem)

class BaseGeneLists extends React.PureComponent {

  static propTypes = {
    projectGuid: PropTypes.string.isRequired,
    canEdit: PropTypes.bool,
    locusListGuids: PropTypes.arrayOf(PropTypes.string),
    loading: PropTypes.bool,
    load: PropTypes.func,
  }

  state = { showAll: false }

  constructor(props) {
    super(props)
    props.load()
  }

  show = () => {
    this.setState({ showAll: true })
  }

  render() {
    const { projectGuid, canEdit, locusListGuids = [], loading } = this.props
    const { showAll } = this.state

    if (loading) {
      return <Dimmer inverted active><Loader content="Loading" /></Dimmer>
    }

    const locusListsToShow = showAll ? locusListGuids : locusListGuids.slice(0, 20)

    return [
      ...locusListsToShow.map(locusListGuid => (
        <LocusList key={locusListGuid} projectGuid={projectGuid} canEdit={canEdit} locusListGuid={locusListGuid} />
      )),
      locusListsToShow.length < locusListGuids.length ?
        <ButtonLink key="show" padding="15px 0 0 0" color="grey" onClick={this.show}>Show More...</ButtonLink> :
        null,
    ]
  }

}

const mapGeneListsStateToProps = (state) => {
  const { projectGuid, canEdit, locusListGuids } = getCurrentProject(state)
  return { projectGuid, canEdit, locusListGuids, loading: getProjectLocusListsIsLoading(state) }
}

const mapGeneListsDispatchToProps = {
  load: loadProjectLocusLists,
}

export const GeneLists = connect(mapGeneListsStateToProps, mapGeneListsDispatchToProps)(BaseGeneLists)

const LOCUS_LIST_FIELDS = [{
  name: 'locusListGuids',
  component: LocusListTables,
  basicFields: true,
  maxHeight: '500px',
  validate: validators.requiredList,
  parse: value => Object.keys(value || {}).filter(locusListGuid => value[locusListGuid]),
  format: value => (value || []).reduce((acc, locusListGuid) => ({ ...acc, [locusListGuid]: true }), {}),
}]

const LocustListsContainer = ({ projectName, children }) => (
  <LocusListsLoader>
    {`Add an existing Gene List to ${projectName} or `}
    <CreateLocusListButton />
    {children}
  </LocusListsLoader>
)

LocustListsContainer.propTypes = {
  projectName: PropTypes.string,
  children: PropTypes.node,
}

const AddGeneLists = React.memo(({ projectGuid, name, onSubmit }) => (
  <UpdateButton
    modalTitle="Add Gene Lists"
    modalId={`add-gene-list-${projectGuid}`}
    formMetaId={projectGuid}
    modalSize="large"
    buttonText="Add Gene List"
    editIconName="plus"
    formContainer={<LocustListsContainer projectName={name} />}
    onSubmit={onSubmit}
    formFields={LOCUS_LIST_FIELDS}
    showErrorPanel
  />
))

AddGeneLists.propTypes = {
  projectGuid: PropTypes.string,
  name: PropTypes.string,
  onSubmit: PropTypes.func,
}

const mapButtonStateToProps = (state) => {
  const { projectGuid, name } = getCurrentProject(state)
  return { projectGuid, name }
}

const mapDispatchToProps = { onSubmit: updateLocusLists }

export const AddGeneListsButton = connect(mapButtonStateToProps, mapDispatchToProps)(AddGeneLists)
