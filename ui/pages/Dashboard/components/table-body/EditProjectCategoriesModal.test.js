import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { EditProjectCategoriesModalComponent } from './EditProjectCategoriesModal'
import { getProjectsByGuid, getModalProjectGuid, getModalDialogState } from '../../redux/rootReducer'

import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

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
