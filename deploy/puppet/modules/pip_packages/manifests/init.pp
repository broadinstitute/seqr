class pip_packages {    

#    exec {"pip-install-virtualenv":
#            command => "/usr/local/bin/pip install virtualenv",
#            creates => '/usr/bin/virtualenv',
#            require => Exec[ 'install-python' ],
#            tries => 5;
#    }

    exec {"install-pip-packages-1":
            command => "/usr/local/bin/pip install -U -r ${xbrowse_repo_dir}/server_requirements_prereqs.txt",
            require => Exec[ 'install-python' ],
    }

    exec {"install-pip-packages-2":
            command => "/usr/local/bin/pip install -U -r ${xbrowse_repo_dir}/server_requirements.txt",
            require => Exec[ 'install-pip-packages-1' ],
    }

}