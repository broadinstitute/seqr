

node default {

    $server_type = 'ec2'
    $hostname = 'xbrowse'
    $fqdn = 'xbrowse.local'
    $base_url = 'http://xbrowse.broadinstitute.org'
    $user = 'root'
    $gunicorn_num_workers = '4'
    $enable_ssl = false

    # file paths - these map to Ben's proposed directory organization
    $provisioning_base_dir = '/mnt'
    $xbrowse_repo_dir = '/mnt/code/xbrowse'
    $xbrowse_working_dir = '/mnt/code/xbrowse'
    $xbrowse_settings_dir = '/mnt/code/xbrowse-settings'
    $projects_dir = '/mnt/projects'
    $raw_data_dir = '/mnt/data/reference_data'
    $puppet_working_dir = '/mnt/code/xbrowse'

    $mongodb_dbpath = '/mnt/mongodb'

    class {'base':
    }

}
