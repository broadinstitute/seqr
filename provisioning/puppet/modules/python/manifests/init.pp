
class python {

    package {
        'readline': ensure => 'latest';
        'readline-devel': ensure => 'latest';
        'bzip2-libs': ensure => 'latest';
        'bzip2-devel': ensure => 'latest';
        'gdbm': ensure => 'latest';
        'gdbm-devel': ensure => 'latest';
        'mysql-devel': ensure => 'latest';
        'freetype': ensure => 'latest';
        'freetype-devel': ensure => 'latest';
        'python-devel': ensure => 'latest';
        'sqlite': ensure => 'latest';
        'sqlite-devel': ensure => 'latest';
        'openssl-devel': ensure => 'latest'; # openssl proper is delcared in modules/tools
        'ncurses-libs': ensure => 'latest';
        'ncurses-devel': ensure => 'latest';
    }

    exec {
        'install-python':
            command => 'wget http://www.python.org/ftp/python/2.7.8/Python-2.7.8.tgz && tar -xzf Python-2.7.8.tgz && cd Python-2.7.8 && ./configure --prefix=/usr/local && make && make altinstall',
            cwd => '/tmp',
            provider => 'shell',
            logoutput => true,
            require => Package[
                'readline',
                'readline-devel',
                'bzip2-libs',
                'bzip2-devel',
                'freetype',
                'freetype-devel',
                'gdbm',
                'gdbm-devel',
                'mysql-devel',
                'python-devel',
                'sqlite',
                'sqlite-devel',
                'openssl-devel',
                'ncurses-libs',
                'ncurses-devel'
            ],
            timeout => 1800,
            creates => '/usr/local/bin/python2.7';
    }

    file { "/etc/environment":
        content => inline_template("PYTHONPATH=<%= @xbrowse_repo_dir %>:<%= @execution_dir %>"),
        require => Exec[ 'install-python' ],
    }

    exec {
        'install-setuptools':
            command => "cd ${execution_dir} && wget --no-check-certificate https://pypi.python.org/packages/source/s/setuptools/setuptools-1.4.2.tar.gz && tar -xzf setuptools-1.4.2.tar.gz && cd setuptools-1.4.2 && /usr/local/bin/python2.7 setup.py install",
            cwd => '/tmp',
            provider => 'shell',
            logoutput => true,
            creates => '/usr/local/lib/python2.7/site-packages/setuptools.pth',
            require => Exec[ 'install-python' ],
            timeout => 1800,
    }

    exec { "install-pip-2.7-binary":
        command => "cd ${execution_dir} && curl https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | /usr/local/bin/python2.7 -",
        creates => "/usr/local/bin/pip",
        provider => 'shell',
        require => Exec[ 'install-setuptools' ],
        tries => 5;
    }

}
