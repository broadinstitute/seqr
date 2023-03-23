import React from 'react'
import PropTypes from 'prop-types'
import { Button, Segment } from 'semantic-ui-react'

import DispatchRequestButton from 'shared/components/buttons/DispatchRequestButton'
import ProjectSelector from 'shared/components/page/ProjectSelector'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

const onSubmit = projectGuid => () => new HttpRequestHelper(`/api/data_management/write_pedigree/${projectGuid}`).get()

const WritePedigree = ({ project }) => (project ? (
  <DispatchRequestButton onSubmit={onSubmit(project.guid)} buttonContainer={<Segment basic />}>
    <Button primary content={`Write Pedigree for ${project.title}`} />
  </DispatchRequestButton>
) : null)

WritePedigree.propTypes = {
  project: PropTypes.object,
}

export default () => <ProjectSelector layout={WritePedigree} />
