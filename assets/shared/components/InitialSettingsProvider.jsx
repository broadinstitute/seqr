import React from 'react'


class InitialSettingsProvider extends React.Component {

    constructor(props) {
        super(props)

        this.state = {
            initialized: false,
            error: null
        }

        // check if initialSettings already embedded in page
        if(window.initialJSON) {
            this.initialSettings = window.initialJSON;
            this.setState({initialized: true})
            return
        }

        // retrieve initialSettings from server since they weren't embedded in the page
        this.initialSettings = {};

        // fetch logged-in user info
        fetch('/seqr/api/user', {credentials: 'include'}).then((response) => {
            return response.json()
        }).then((responseJSON) => {
            console.log("Setting state to: ", responseJSON)
            for (var k in responseJSON) {
                this.initialSettings[k] = responseJSON[k]
            }

            // fetch additional info if url provided in page
            if(window.initialUrl) {
                return fetch(window.initialUrl, {credentials: 'include'})
            } else {
                this.setState({initialized: true})
                throw "exit"
            }
        }).then((response) => {
            return response.json()
        }).then((responseJSON) => {
            console.log("Setting state to: ", responseJSON)
            for (var k in responseJSON) {
                this.initialSettings[k] = responseJSON[k]
            }

            this.setState({initialized: true})

        }).catch((exception) => {

            if(exception == "exit") {
                return
            } else {
                this.setState({error: exception})
            }
        })
    }

    render() {
        if(this.state.initialized) {
            return React.cloneElement(this.props.children, {
                initialSettings: this.initialSettings
            })

        } else {
            if(!this.state.error) {
                return <div style={{padding:"100px", width:"100%"}}><center>Loading ... </center></div>
            } else {
                return <div>Error: {this.state.error}</div>
            }
        }
    }
}

InitialSettingsProvider.propTypes = {
    children: React.PropTypes.element.isRequired  //require 1 child component
}

export default InitialSettingsProvider
