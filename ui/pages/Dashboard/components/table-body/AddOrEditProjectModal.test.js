import React from 'react'
import { shallow } from 'enzyme'
import { AddOrEditProjectModalComponent } from './AddOrEditProjectModal'
import { getModalDialogState, getProjectsByGuid, getModalProjectGuid } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    modalDialogState: PropTypes.object.isRequired,
    project: PropTypes.object,
    hideModal: PropTypes.func.isRequired,
    updateProjectsByGuid: PropTypes.func.isRequired,
   */

  const props = {
    modalDialogState: getModalDialogState(STATE1),
    project: getProjectsByGuid(STATE1)[getModalProjectGuid(STATE1)],
    hideModal: () => {},
    updateProjectsByGuid: () => {},
  }

  shallow(<AddOrEditProjectModalComponent {...props} />)
})
