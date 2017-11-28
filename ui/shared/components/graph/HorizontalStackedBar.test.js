import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import HorizontalStackedBar from './HorizontalStackedBar'

configure({ adapter: new Adapter() })

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
