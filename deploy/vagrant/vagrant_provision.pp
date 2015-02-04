Exec { path => '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' }
File { owner => 'root', group => 'root', mode => '644' }
Package { allow_virtual => false }

node default {

    $server_type = 'vagrant'
    $hostname = 'xbrowse'
    $fqdn = 'xbrowse.local'
    $user = 'vagrant'
    $gunicorn_num_workers = '4'
    $enable_ssl = false

    # this is the base directory of the xbrowse repository
    $xbrowse_repo_dir = '/vagrant/xbrowse'

    # this is the directory where scripts like management commands are executed from
    # this is a relic from the old Vagrant VM, where everything was run in the /home/vagrant
    # I'm not sure what the 'right' directory is to run these things on a server like xbrowse -
    # since ideally we'd have multiple servers / containers doing the various tasks
    $execution_dir = '/home/vagrant'

    # this is the base directory of the xbrowse repository
    $raw_data_dir = '/vagrant/xbrowse-laptop-downloads'

    # base URL of xbrowse instance - ie. the URL user sees when opens homepage
    $base_url = '192.168.50.101'

    class {'base': }

}


