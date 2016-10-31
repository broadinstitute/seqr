import React from 'react';
import ReactDOM from 'react-dom';
import { Router, Route, hashHistory } from 'react-router'
import BaseLayout from '../../components/base-layout';
import Login from './components/login';



ReactDOM.render(
    <BaseLayout>
        <Login/>
    </BaseLayout>,
    document.getElementById('reactjs-root'))
