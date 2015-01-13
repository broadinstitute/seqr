class symlink {
    
    file { "${execution_dir}/manage.py":
        ensure => link,
        target => "${xbrowse_repo_dir}/manage.py",
    }

    file { "${execution_dir}/wsgi.py":
        ensure => link,
        target => "${xbrowse_repo_dir}/wsgi.py"
    }

}