

node default {

    $server_type = 'ec2'
    $hostname = 'xbrowse'
    $fqdn = 'xbrowse.local'
    $user = 'root'
    $gunicorn_num_workers = '4'
    $xbrowse_repo_dir = '/mnt/xbrowse-puppet/xbrowse'
    $provisioning_base_dir = '/mnt/xbrowse-puppet'
    $execution_dir = '/mnt'
    $raw_data_dir = '/mnt/xbrowse-laptop-downloads'
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
