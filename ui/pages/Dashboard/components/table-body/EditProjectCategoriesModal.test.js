import React from 'react'
import { shallow } from 'enzyme'
import { EditProjectCategoriesModalComponent } from './EditProjectCategoriesModal'
import { getProjectsByGuid, getModalProjectGuid, getModalDialogState } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    modalDialogState: PropTypes.object,
    project: PropTypes.object,
    hideModal: PropTypes.func.isRequired,
    updateProjectsByGuid: PropTypes.func.isRequired,
    updateProjectCategoriesByGuid: PropTypes.func.isRequired,
   */

  const props = {
    project: getProjectsByGuid(STATE1)[getModalProjectGuid(STATE1)],
    modalDialogState: getModalDialogState(STATE1),
    hideModal: () => {},
    updateProjectsByGuid: () => {},
    updateProjectCategoriesByGuid: () => {},
  }

  shallow(<EditProjectCategoriesModalComponent {...props} />)
})
