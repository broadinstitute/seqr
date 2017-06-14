import React from 'react'
import { shallow } from 'enzyme'
import { FilterSelectorComponent } from './FilterSelector'
import { SHOW_ALL } from '../../constants'
import { getProjectCategoriesByGuid } from '../../reducers/rootReducer'
import { STATE1 } from '../../fixtures'


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
