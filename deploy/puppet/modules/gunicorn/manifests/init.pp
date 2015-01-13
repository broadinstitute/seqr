
class gunicorn {

    file { "${execution_dir}/gunicorn_config.py":
            content => template("gunicorn/gunicorn_config.py"),
            owner => $user,
            ensure => present,
    }

    file { "/etc/supervisord.d/gunicorn.conf":
            content => template("gunicorn/gunicorn.conf"),
            owner => $user,
            ensure => present,
    }

}
