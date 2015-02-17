

node default {

    $server_type = 'ec2'
    $hostname = 'xbrowse'
    $fqdn = 'xbrowse.local'
    $base_url = 'http://xbrowse.broadinstitute.org'
    $user = 'root'
    $gunicorn_num_workers = '4'
    $enable_ssl = false

    $xbrowse_repo_dir = '/mnt/code/xbrowse'
    $provisioning_base_dir = '/mnt'
    $execution_dir = '/mnt'
    $raw_data_dir = '/mnt/data/reference_data'
    $mongodb_dbpath = '/mnt/mongodb'

    class {'base':
    }

}
