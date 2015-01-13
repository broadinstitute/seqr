class supervisord {
    
    exec {'install-supervisord':
        command => '/usr/local/bin/easy_install supervisor',
        provider => 'shell',
    }

    exec {'make-supervisord-directory':
        command => 'mkdir /etc/supervisord.d/',
        provider => 'shell',
        creates => '/etc/supervisord.d',
        require => Exec[ 'install-supervisord' ],
    }

    exec {'supervisord-conf':
        command => 'sh -c "/usr/local/bin/echo_supervisord_conf > /etc/supervisord.conf"',
        provider => 'shell',
        require => Exec[ 'make-supervisord-directory' ],
    }

    exec {'include-supervisord-conf':
        command => 'sh -c "echo \"[include]\" >> /etc/supervisord.conf"',
        provider => 'shell',
        require => Exec[ 'supervisord-conf' ],
    }

    exec {'etc-supervisord-conf':
        command => 'sh -c "echo \"files = /etc/supervisord.d/*.conf\" >> /etc/supervisord.conf"',
        provider => 'shell',
        require => Exec[ 'include-supervisord-conf' ],
    }

    file {"/etc/init.d/supervisord":
            ensure => present,
            mode => 0755,
            content => template("supervisord/init.d"),
            require => Exec[ 'install-supervisord' ];
    }

    file {'/tmp/supervisor.sock':
        ensure => present,
        owner => $user,
        require => Exec[ 'install-supervisord' ],
    }

    service {'supervisord':
        require => [File[ '/etc/init.d/supervisord',
                            '/tmp/supervisor.sock' ], 
                            Exec[ 'etc-supervisord-conf' ]],
        ensure => running,
        hasstatus => true;
    }

}