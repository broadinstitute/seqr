#By default, we run these commands as root. If we want a file to be owned by Vagrant,
#we do it on the individual provisioning method.
Exec { path => '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' }
File { owner => 'root', group => 'root', mode => '644' }
Package { allow_virtual => false }

class stages {
    stage { 'bootstrap':  before => Stage['main'] }
    stage { 'cleanup': require => Stage['main'] }
}

class base {

    include stages
    include epel

    class {'::mongodb::server':
      dbpath => $mongodb_dbpath,
    }
    class {'::mongodb::client': }

    class { 'tools': stage => 'bootstrap' }
    class { 'python':
      stage => 'bootstrap',
      require => [Class['tools']]}

    class { 'perl': }
    class { 'yum_packages': }

    class { 'pip_packages':
            require => [Class[ 'yum_packages' ],
                        Class[ 'python' ]]}

    class { 'postgresql': }
    class { 'xbrowse_settings': }

    class { 'django':
            require => [Class[ 'pip_packages' ],
                        Class[ 'xbrowse_settings' ],
                        Class[ 'yum_packages' ]]}

    class { 'nginx': serve_local => false,
                require => Class[ 'django' ], }

    class { 'gunicorn':
                require => Class[ 'nginx' ],}

    class { 'supervisord':
                require => [Class[ 'gunicorn' ]]}

}
