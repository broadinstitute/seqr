
# Global Debian package dependencies

class yum_packages {
    
    package { 'libjpeg-turbo': ensure => latest }
    package { 'libjpeg-turbo-devel': ensure => latest }
    package { 'libpng': ensure => latest }
    package { 'libpng-devel': ensure => latest }
    package { 'zlib': ensure => latest }
    package { 'zlib-devel': ensure => latest }

}
