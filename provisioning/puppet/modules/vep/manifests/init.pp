class vep {

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

    file { 'variant_effect_predictor.tar.gz':
        path => "${execution_dir}/variant_effect_predictor.tar.gz",
        ensure => present,
        source => "${raw_data_dir}/variant_effect_predictor.tar.gz",
        require => Exec[ 'extract-CGI-time' ],
    }

    exec { 'untar-variant-predictor':
        command => "tar -xzf ${execution_dir}/variant_effect_predictor.tar.gz -C ${execution_dir}",
        creates => "${execution_dir}/variant_effect_predictor/",
        require => File[ "${execution_dir}/variant_effect_predictor.tar.gz" ],
    }

    exec { 'perl-install-variant':
        command => "perl ${execution_dir}/variant_effect_predictor/INSTALL.pl",
        cwd => "${execution_dir}/variant_effect_predictor",
        require => Exec[ 'untar-variant-predictor' ],
        creates => "${execution_dir}/variant_effect_predictor/Bio",
    }

}

