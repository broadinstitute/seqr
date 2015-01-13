class django {
    
    exec {"update-python-path":
        command => 'export PYTHONPATH=$PYTHONPATH:${xbrowse_repo_dir}',
        provider => 'shell',
    }

}