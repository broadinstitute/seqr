import React from 'react';
import { Provider } from 'react-redux'

import BaseLayout from './BaseLayout'

const Root = ({store, children}) => {
    return <Provider store={store}>
        <BaseLayout>
            {children}
        </BaseLayout>
    </Provider>
}

export default Root;