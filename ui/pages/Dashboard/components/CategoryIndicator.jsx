import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import randomMC from 'random-material-color'
import styled from 'styled-components'
import { Icon } from 'semantic-ui-react'

import { getProjectCategoriesByGuid } from 'redux/selectors'
import EditProjectCategoriesModal from './EditProjectCategoriesModal'

const getColor = categoryNames => (
  categoryNames.length === 0 ? '#ccc' : randomMC.getColor({ shades: ['300', '400', '500', '600', '700', '800'], text: categoryNames.sort().join(',') })
)

const ComputedColoredIcon = styled(({ categoryNames, ...props }) => <Icon {...props} />)`
  color: ${props => getColor(props.categoryNames)} !important;
`

const CategoryIndicator = React.memo(({ project, projectCategoriesByGuid }) => {
  const categoryNames = project.projectCategoryGuids.map(guid => (projectCategoriesByGuid[guid] && projectCategoriesByGuid[guid].name) || guid)

  const popup = categoryNames.length > 0 ? {
    content: categoryNames.map(name => <div key={name}>{name}</div>),
    header: 'Categories',
    position: 'top center',
    size: 'small',
  } : null

  return (
    <EditProjectCategoriesModal
      project={project}
      trigger={
        <a role="button" tabIndex="0" style={{ cursor: 'pointer' }}>
          <ComputedColoredIcon name={`${categoryNames.length === 0 ? 'empty ' : ''}star`} categoryNames={categoryNames} />
        </a>
      }
      popup={popup}
      triggerName="categoryIndicator"
    />
  )
})

CategoryIndicator.propTypes = {
  project: PropTypes.object.isRequired,
  projectCategoriesByGuid: PropTypes.object.isRequired,
}

export { CategoryIndicator as CategoryIndicatorComponent }

const mapStateToProps = state => ({ projectCategoriesByGuid: getProjectCategoriesByGuid(state) })

export default connect(mapStateToProps)(CategoryIndicator)

