
class tools {

    file {
        '/etc/ssh/ssh_known_hosts':
            source => 'puppet:///modules/tools/ssh_known_hosts';
    }

    package { 'gcc': ensure => latest }
    package { 'gcc-c++': ensure => latest }
    package { 'kernel-devel': ensure => latest }
    package { 'glibc-devel': ensure => latest }
    package { 'glibc-headers': ensure => latest }
    package { 'make': ensure => latest }

    package { 'gnupg2': ensure => latest }
    package { 'openssl': ensure => latest } 
    package { 'git': ensure => latest }
    package { 'wget': ensure => latest }
    package { 'curl': ensure => latest }
    package { 'nc': ensure => latest }
    package { 'nmap': ensure => latest }
    package { 'vim-enhanced': ensure => latest }
    package { 'telnet': ensure => latest }
    package { 'iotop': ensure => latest }
    package { 'lsof': ensure => latest }
    package { 'bc': ensure => latest }
    package { 'unzip': ensure => latest }
    package { 'libaio': ensure => latest }
    
    exec {'groupinstall-development':
            command => 'yum groupinstall -y development',
            provider => 'shell',
    }

    exec {'groupinstall-development-tools':
            command => 'yum groupinstall "Development Tools"',
            provider => 'shell',
            creates => ['/usr/bin/bison',
                        '/usr/bin/byacc',
                        '/usr/bin/cscope',
                        '/usr/bin/ctags',
                        '/usr/bin/cvs',
                        '/usr/bin/diffstat',
                        '/usr/bin/doxygen',
                        '/usr/bin/flex',
                        '/usr/bin/gcc',
                        '/usr/bin/gcc-c++',
                        '/usr/bin/gcc-gfortran',
                        '/usr/bin/gettext',
                        '/usr/bin/git',
                        '/usr/bin/indent',
                        '/usr/bin/intltool',
                        '/usr/bin/libtool',
                        '/usr/bin/patch',
                        '/usr/bin/patchutils',
                        '/usr/bin/rcs',
                        '/usr/bin/redhat-rpm-config',
                        '/usr/bin/rpm-build',
                        '/usr/bin/subversion',
                        '/usr/bin/swig',
                        '/usr/bin/systemtap']
    }
}
