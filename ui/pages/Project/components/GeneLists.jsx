import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getProject } from 'redux/rootReducer'

const GeneListContainer = styled.div`
  margin-bottom: 14px;
`
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
  <GeneListContainer>
    {
      props.project.locusLists &&
      props.project.locusLists.map(locusList => (
        <ItemContainer key={locusList.locusListGuid}>
          {locusList.name}
          <span style={{ paddingLeft: '10px' }}>
            <i>
              <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>
                {`${locusList.numEntries} entries`}
              </a>
            </i>
          </span>
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
  </GeneListContainer>
)


GeneLists.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(GeneLists)
