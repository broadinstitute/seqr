import React from 'react';
import BasicDataTable from '../../../components/BasicDataTable.jsx';

module.exports = React.createClass({

    getInitialState: function() {

        return window.initial_json;
    },

    render: function() {
        let to_date_string = (d) => {
            let am_or_pm = d.getHours() < 12 ? "am" : "pm";
            let year = d.getFullYear();
            let month = (d.getMonth()+1 < 10 ? " " : "") + (d.getMonth()+1);
            let minutes = (d.getMinutes() < 10 ? "0" : "") + d.getMinutes();
            let hours = d.getHours();
            if(hours == 0) {
                hours = 12;
            } else if(hours > 12) {
                hours = hours - 12;
            }
            return year+"."+month+"."+d.getDate()+"    "+hours+":"+minutes+" "+am_or_pm;
        };

        return <div className="families-table " style={{marginLeft:"15px", marginRight:"15px", width:'100%'}}>
                <BasicDataTable title="Families" id="families-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th className="collapsing">Family (and pedigree)</th>
                        <th className="collapsing">Individuals</th>
                        <th className="collapsing">Description</th>
                        <th className="collapsing">Status</th>
                    </tr>
                </thead>
                <tbody id="table-body">
                {
                    this.state ?
                        this.state.families.map(function(project) {
                            return <tr key={project["project_id"]}>
                                <td style={{width :"180px"}}>
                                    <a href={'/project/'+project['project_id']} style={{marginRight: "10px", fontWeight: "bold"}}>
                                        {project["project_name"] || project["project_id"]}
                                    </a>
                                    {project["description"]}
                                </td>
                                <td style={{verticalAlign:"top"}}>{project["num_families"]}</td>
                                <td style={{verticalAlign:"top"}}>{project["num_individuals"]}</td>
                                <td style={{verticalAlign:"top", whiteSpace:"pre"}}>
                                    {to_date_string(new Date(project["created_date"] || project["last_accessed_date"]))}
                                </td>
                            </tr>
                        }) : null
                }
                </tbody>
                <tfoot className="full-width"><tr></tr></tfoot>
            </BasicDataTable>
            <br />
            <div className="ui small basic blue labeled icon button" id="create-project-button">
                <i className="add icon"></i> Create New Project
            </div>
        </div>
    },
});


