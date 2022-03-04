import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { PageHeaderComponent } from './Header'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    user: PropTypes.object.isRequired,
   */

  const props = {
    user: {
      date_joined: '2015-02-19T20:22:50.633Z',
      email: 'seqr+test@populationgenomics.org.au',
      first_name: '',
      id: 1,
      is_active: true,
      last_login: '2017-03-14T17:44:53.403Z',
      last_name: '',
      username: 'test',
    },
  }

  shallow(<PageHeaderComponent {...props} />)
})
