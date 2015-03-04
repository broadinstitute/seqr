
class xbrowse_settings {

    file { 'annotator_settings':
        path => "${execution_dir}/annotator_settings.py",
        ensure => present,
        content => template("xbrowse_settings/annotator_settings.py")
    }

    file { 'cnv_store_settings':
        path => "${execution_dir}/cnv_store_settings.py",
        ensure => present,
        content => template("xbrowse_settings/cnv_store_settings.py"),
    }

    file { 'cnv_store_settings':
        path => "${execution_dir}/custom_annotator_settings.py",
        ensure => present,
        content => template("xbrowse_settings/custom_annotator_settings.py"),
    }

    file { 'local_settings':
        path => "${execution_dir}/local_settings.py",
        ensure => present,
        content => template("xbrowse_settings/local_settings.py"),
    }

    file { 'reference_settings':
        path => "${execution_dir}/reference_settings.py",
        ensure => present,
        content => template("xbrowse_settings/reference_settings.py"),
    }

}