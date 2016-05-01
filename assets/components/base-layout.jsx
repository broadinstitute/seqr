import React from 'react'
import Header from './header';
import Footer from './footer';

module.exports = React.createClass({
    render: function () {

        return <div style={{height:'calc(100% - 40px)'}}>
                <Header/>

                <div className="ui grid" style={{minHeight:'calc(100% - 40px)'}}>
                    <div className="two wide column"></div>
                    <div className="twelve wide column" style={{ marginTop: "30px"}}>
                        {this.props.children}
                    </div>
                    <div className="two wide column"></div>
                </div>
            <Footer/>
        </div>
    }
})