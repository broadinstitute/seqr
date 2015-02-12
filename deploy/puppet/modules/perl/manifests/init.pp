class perl {

    Exec { path => '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' }
    File { owner => 'root', group => 'root', mode => '644' }
    Package { allow_virtual => false }

    package { 'perl-DBI': ensure => latest }
    package { 'perl-devel': ensure => latest }
    package { 'perl-CPAN': ensure => latest }

    exec { 'cpanmin':
        command => 'curl -L http://cpanmin.us | perl - --sudo App::cpanminus',
        provider => 'shell',
        require => Package[ 'perl-DBI',
                            'perl-devel',
                            'perl-CPAN'],
        creates => '/usr/local/bin/cpanm',
    }

    exec { 'extract-CGI-time':
        command => '/usr/local/bin/cpanm Archive::Extract CGI Time::HiRes',
        provider => 'shell',
        require => Exec[ 'cpanmin' ],
    }

}

