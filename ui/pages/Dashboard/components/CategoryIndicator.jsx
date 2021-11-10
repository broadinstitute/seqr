import React from 'react'
import PropTypes from 'prop-types'
import { Loader } from 'semantic-ui-react'

import { ButtonLink } from 'shared/components/StyledComponents'
import EditProjectCategoriesModal from './EditProjectCategoriesModal'

const ComputedColoredIcon = React.lazy(() => import('./ComputedColoredIcon'))

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
        <ButtonLink>
          <React.Suspense fallback={<Loader />}>
            <ComputedColoredIcon
              name={`${project.projectCategories.length === 0 ? 'outline ' : ''}star`}
              categoryNames={project.projectCategories}
            />
          </React.Suspense>
        </ButtonLink>
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
