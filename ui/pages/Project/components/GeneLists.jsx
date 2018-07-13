import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'

import LocusListGeneDetail from 'shared/components/panel/genes/LocusListGeneDetail'
import ButtonLink from 'shared/components/buttons/ButtonLink'
import Modal from 'shared/components/modal/Modal'
import { HorizontalSpacer } from 'shared/components/Spacers'
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
            modalName={`${locusList.name}-genes`}
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
  </div>
)


GeneLists.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(GeneLists)
