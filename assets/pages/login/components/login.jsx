import React from 'react';


module.exports = React.createClass({

    render: function () {
        console.log("PROPS: ", this.props)
        var errorMessageDisplayState = this.props.loginErrorMessage == null ? 'none' : 'block';
        return  <div>
            <div className="row">
                <center>
                    <div style={{fontSize: '80px', 'padding': '15px 0 0 0'}}>seqr</div>
                    <div /><br/><br/><br/>
                    <div style={{fontSize: '24px', fontWeight: '300', paddingBottom: '10px'}}>
                        An <a href="https://github.com/macarthur-lab/seqr">open source software</a> platform for rare disease genomics
                    </div>
                </center>
            </div>
            <div className="ui divider"></div>
            <div className="row">
                <div className="ui stackable two column grid">
                    <div className="column">
                        <ul style={{fontSize:'16px', 'fontWeight':300, 'marginTop': '0px'}}>
                            <li><strong>Identify disease causing variants:</strong> Search for
                                variant(s) that cause Mendelian disease in a family or individual, using
                                community best practices for prioritizing variants.
                            </li>
                            <br/>
                            <li><strong>Integrate different data sources:</strong> Browse contextual
                                information for variants and genes such as population allele
                                frequencies, OMIM and clinvar status, gene expression, etc.
                            </li>
                            <br/>
                            <li><strong>Collaborate to solve cases:</strong> Grant colleagues access to
                                your data, and collaborate to tag variants.
                            </li>
                            <br/>
                        </ul>
                    </div>
                    <div className="column">
                        <strong>Recommended:</strong><br/>
                        <br/>
                        {/* use pre-sized 40px div so components below don't shift after the google Sign-in button finishes loading */}
                        <div style={{height:'40px'}}>
                            <div id="google-signin2" style={{marginLeft:'20px'}}></div>
                        </div>

                        <div className="ui horizontal divider">OR</div>

                        <strong>Log in:</strong><br/>
                        <form className="ui form" id="login-form" style={{padding:'0px 10px 10px 10px'}}>

                            <div className="sixteen wide field">{/* without this div, the 1st field isn't aligned correctly */}</div>
                            <div className="thirteen wide field" style={{marginBottom:'0.66em'}}>
                                <input type="text" style={{height:'32px'}} name="username"
                                       placeholder="UserID or Email"/>
                            </div>
                            <div className="thirteen wide field">
                                <input type="password" style={{height:'32px'}} name="password"
                                       placeholder="Password"/>
                            </div>
                            <div className="thirteen wide field">
                                    <div className="ui error message" style={{display: errorMessageDisplayState}}>{this.props.loginErrorMessage}</div>
                            </div>
                            <div className="field">
                                <div className="ui submit button" style={{background:'#4285F4', color: 'white'}}>Sign in</div>
                            </div>

                            <input type="hidden" name="next" value="/"/>
                            <br/>
                            <div className="field">

                                <a href="#" id="forgot-user-pass">Forgot your password?</a><br/>
                                <br/>
                                Don't have an account? &nbsp; <a href="/signup">Sign up now</a>
                                &nbsp; (or just Sign In using Google above)
                            </div>

                        </form>
                    </div>
                </div>
            </div>
        </div>
    },


    getInitialState: function() {
        return { loginErrorMessage : "bla" }
    },


    componentDidMount: function () {

        $('#login-form').form({
            fields: {
                    username: 'empty',
                    password: 'empty'
                },
            }, {
                onFailure: function () {
                    this.props.loginErrorMessage = null;
                    return false;   //prevent default form action
                },
                onSuccess: function () {
                    //validation succeeded
                    $.ajax({
                        url: '/',
                        type: 'post',
                        data: $('#login-form').form('get values'),
                        success: function (data, textStatus, jqXHR) {
                            console.log(data);
                            console.log(textStatus);
                            console.log(jqXHR);

                            window.location.reload(); //reload the page which will cause the server-side view to redirect
                        },
                        error: function (jqXHR, textStatus, errorThrown) {
                            if (jqXHR.status == 403) {
                                // handle invalid login response
                                this.props.loginErrorMessage = "Invalid username or password";
                                $('#login-form').find(":input[name='username']").closest(".field").addClass("error");
                                $('#login-form').find(":input[name='password']").closest(".field").addClass("error")
                            } else if (jqXHR.status == 0) {
                                //handle unexpected error
                                this.props.loginErrorMessage = "<b>Error: </b> Could not connect to server";
                            } else {
                                this.props.loginErrorMessage = "<b>Error: </b> Unexpected error occurred";
                                console.log(jqXHR.status);
                                console.log(textStatus);
                                console.log(errorThrown);
                            }
                        }
                    });

                    return false; //prevent default form action
                }
            }
        );

        $('#forgot-user-pass').click(function () {
            console.log("show modal");
            $('#reset-password-modal').modal({
                onApprove: function () {
                    alert("Not yet implemented.");
                    return true;
                }
            }).modal('show');

            return false;
        });

    }

});


