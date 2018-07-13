import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon, Button, Divider } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { setModalConfirm } from 'redux/utils/modalReducer'
import { LocusListsLoader } from 'shared/components/LocusListLoader'
import LocusListGeneDetail from 'shared/components/panel/genes/LocusListGeneDetail'
import LocusListTables from 'shared/components/table/LocusListTables'
import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import ButtonLink from 'shared/components/buttons/ButtonLink'
import Modal from 'shared/components/modal/Modal'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import {
  LOCUS_LIST_IS_PUBLIC_FIELD_NAME, LOCUS_LIST_LAST_MODIFIED_FIELD_NAME, LOCUS_LIST_CURATOR_FIELD_NAME,
} from 'shared/utils/constants'
import { getProject } from '../selectors'
import { updateLocusLists } from '../reducers'

const ItemContainer = styled.div`
  padding: 2px 0px;
  whitespace: nowrap;
`
const HelpIcon = styled(Icon)`
  cursor: pointer;
  color: #555555; 
  margin-left: 10px;
`

const OMIT_LOCUS_LIST_FIELDS = [
  LOCUS_LIST_IS_PUBLIC_FIELD_NAME,
  LOCUS_LIST_LAST_MODIFIED_FIELD_NAME,
  LOCUS_LIST_CURATOR_FIELD_NAME,
]

class BaseAddLocusListModal extends React.PureComponent {

  static propTypes = {
    project: PropTypes.object,
    updateLocusLists: PropTypes.func,
    setModalConfirm: PropTypes.func,
  }

  constructor(props) {
    super(props)

    this.state = {
      selected: {},
    }
    this.modalName = `${props.project.projectGuid}-add-gene-list`
  }

  selectList = (locusListGuids, selected) => {
    const updatedSelected = {
      ...this.state.selected,
      ...locusListGuids.reduce((acc, locusListGuid) => ({ ...acc, [locusListGuid]: selected }), {}),
    }
    this.setState({ selected: updatedSelected })
    this.props.setModalConfirm(
      this.modalName,
      Object.values(updatedSelected).some(isSelected => isSelected) ?
        'Gene lists have not been added. Are you sure you want to close?' : null,
    )
  }

  submit = () => {
    this.props.updateLocusLists({
      locusListGuids: Object.keys(this.state.selected).filter(locusListGuid => this.state.selected[locusListGuid]),
    })
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
            selectRows={this.selectList}
          />
          <Divider />
          <Button content="Submit" primary onClick={this.submit} />
        </LocusListsLoader>
      </Modal>
    )
  }
}

const mapDispatchToProps = {
  setModalConfirm, updateLocusLists,
}

const AddLocusListModal = connect(null, mapDispatchToProps)(BaseAddLocusListModal)

const GeneLists = props => (
  <div>
    {
      props.project.locusLists &&
      props.project.locusLists.map(locusList => (
        <ItemContainer key={locusList.locusListGuid}>
          {locusList.name}
          <HorizontalSpacer width={10} />
          <Modal
            title={`${locusList.name} Gene List`}
            modalName={`${props.project.projectGuid}-${locusList.name}-genes`}
            trigger={<i><ButtonLink>{`${locusList.numEntries} entries`}</ButtonLink></i>}
            size="large"
          >
            <LocusListGeneDetail locusListGuid={locusList.locusListGuid} projectGuid={props.project.projectGuid} />
          </Modal>
          {
            locusList.description &&
            <Popup
              position="right center"
              trigger={<HelpIcon name="help circle outline" />}
              content={locusList.description}
              size="small"
            />
          }
        </ItemContainer>),
      )
    }
    <VerticalSpacer height={15} />
    {props.project.canEdit && <AddLocusListModal project={props.project} />}
  </div>
)


GeneLists.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(GeneLists)
