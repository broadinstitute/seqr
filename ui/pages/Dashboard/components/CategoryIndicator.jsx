import React from 'react'
import PropTypes from 'prop-types'

import randomMC from 'random-material-color'
import styled from 'styled-components'
import { Icon } from 'semantic-ui-react'

import EditProjectCategoriesModal from './EditProjectCategoriesModal'

const getColor = categoryNames => (
  categoryNames.length === 0 ? '#ccc' : randomMC.getColor({ shades: ['300', '400', '500', '600', '700', '800'], text: categoryNames.sort().join(',') })
)

const ComputedColoredIcon = styled(({ categoryNames, ...props }) => <Icon {...props} />)`
  color: ${props => getColor(props.categoryNames)} !important;
`

const CategoryIndicator = React.memo(({ project }) => {
  const popup = project.projectCategories.length > 0 ? {
    content: project.projectCategories.map(name => <div key={name}>{name}</div>),
    header: 'Categories',
    position: 'top center',
    size: 'small',
  } : null

  return (
    <EditProjectCategoriesModal
      project={project}
      trigger={
        <a role="button" tabIndex="0" style={{ cursor: 'pointer' }}>
          <ComputedColoredIcon name={`${project.projectCategories.length === 0 ? 'outline ' : ''}star`} categoryNames={project.projectCategories} />
        </a>
      }
      popup={popup}
      triggerName="categoryIndicator"
    />
  )
})

CategoryIndicator.propTypes = {
  project: PropTypes.object.isRequired,
}

export default CategoryIndicator

