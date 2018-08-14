import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getProjectCategoriesByGuid } from 'redux/selectors'
import { FilterSelectorComponent } from './FilterSelector'
import { SHOW_ALL } from '../constants'
import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    filter: PropTypes.string.isRequired,
    projectCategoriesByGuid: PropTypes.object,
    onChange: PropTypes.func.isRequired,
   */

  const props = {
    filter: SHOW_ALL,
    projectCategoriesByGuid: getProjectCategoriesByGuid(STATE1),
    onChange: () => {},
  }

  shallow(<FilterSelectorComponent {...props} />)
})
