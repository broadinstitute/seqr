import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { getProject } from 'redux/rootReducer'
import ColoredIcon from 'shared/components/icons/ColoredIcon'

const HelpIcon = styled(Icon)`
  cursor: pointer;
  color: #555555; 
  margin-left: 15px;
`

const VariantTags = props => (
  <div key="content" style={{ display: 'block', padding: '0px 0px 10px 0px' }}>
    {
      props.project.variantTagTypes && props.project.variantTagTypes.map(variantTagType => (
        <div key={variantTagType.variantTagTypeGuid} style={{ whitespace: 'nowrap' }}>
          {
            <span style={{ display: 'inline-block', minWidth: '35px', textAlign: 'right', fontSize: '11pt', paddingRight: '10px' }}>
              {variantTagType.numTags > 0 && <span style={{ fontWeight: 'bold' }}>{variantTagType.numTags}</span>}
            </span>
          }
          <ColoredIcon name="square" size="small" styleColor={variantTagType.color} />
          <a href={`/project/${props.project.deprecatedProjectId}/variants/${variantTagType.name}`}>{variantTagType.name}</a>
          {
            variantTagType.description &&
            <Popup
              position="right center"
              trigger={<HelpIcon name="help circle outline" />}
              content={variantTagType.description}
              size="small"
            />
          }
        </div>),
      )
    }
  </div>
)


VariantTags.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(VariantTags)
