import React from 'react'
import { shallow } from 'enzyme'
import HorizontalStackedBar from './HorizontalStackedBar'


test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    data: PropTypes.arrayOf(PropTypes.object),  //an array of objects with keys: name, count, color, percent
    width: PropTypes.number,
    height: PropTypes.number,
   */

  const props = {
    title: 'title',
    data: [
      { name: 'item1', count: 32, color: 'black', percent: 32 },
      { name: 'item2', count: 68, color: 'black', percent: 68 },
    ],
    width: 100,
    height: 5,
  }

  shallow(<HorizontalStackedBar {...props} />)
})
