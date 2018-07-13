import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'

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
    {props.project.canEdit &&
      <Modal
        title="Add Gene List"
        modalName={`${props.project.projectGuid}-add-gene-list`}
        trigger={<ButtonLink>Add Gene List</ButtonLink>}
        size="large"
      >
        Add an existing Gene List to {props.project.name} or <CreateLocusListButton />
        <LocusListsLoader>
          <LocusListTables isEditable={false} showLinks={false} omitFields={OMIT_LOCUS_LIST_FIELDS} />
        </LocusListsLoader>
      </Modal>
    }
  </div>
)


GeneLists.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(GeneLists)
