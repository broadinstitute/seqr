

node default {

    $server_type = 'ec2'
    $hostname = 'xbrowse'
    $fqdn = 'xbrowse.local'
    $base_url = 'http://xbrowse.broadinstitute.org'
    $user = 'root'
    $gunicorn_num_workers = '4'
    $enable_ssl = true

    $xbrowse_repo_dir = '/mnt/code/xbrowse'
    $provisioning_base_dir = '/mnt'
    $execution_dir = '/mnt'
    $raw_data_dir = '/mnt/data'
    $mongodb_dbpath = '/mnt/mongodb'

#    # Drop firewall as we don't need it.
#    exec {
#        'iptables-install':
#            command => 'iptables -F && iptables -A FORWARD -j REJECT && /etc/init.d/iptables save',
#    }

    class {'base':
#        require => Exec[ 'iptables-install' ];
    }

}
