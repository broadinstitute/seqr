class vep {

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

