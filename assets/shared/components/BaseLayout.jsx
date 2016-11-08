import React from 'react'
import Header from './Header';
import Footer from './Footer';

export default ({children}) =>
    <div style={{height:'calc(100% - 40px)'}}>
        <Header/>
        <div className="ui grid" style={{minHeight:'calc(100% - 40px)'}}>
            <div className="one wide column"></div>
            <div className="fourteen wide column" style={{ marginTop: "30px"}}>
                {children}
            </div>
            <div className="one wide column"></div>
        </div>
        <Footer/>
    </div>
