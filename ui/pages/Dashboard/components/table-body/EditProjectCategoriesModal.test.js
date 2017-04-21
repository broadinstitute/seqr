import React from 'react'
import { shallow } from 'enzyme'
import { EditProjectCategoriesModalComponent } from './EditProjectCategoriesModal'
import { getProjectsByGuid, getModalProjectGuid, getModalDialogState } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    modalDialogState: React.PropTypes.object,
    project: React.PropTypes.object,
    hideModal: React.PropTypes.func.isRequired,
    updateProjectsByGuid: React.PropTypes.func.isRequired,
    updateProjectCategoriesByGuid: React.PropTypes.func.isRequired,
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
