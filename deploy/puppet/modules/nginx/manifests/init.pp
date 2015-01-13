
class nginx ( $serve_local) {

    
    file {

        "/etc/yum.repos.d/nginx.repo":
            ensure => present,
            source => 'puppet:///modules/nginx/nginx.repo',
            notify => Package[ 'nginx' ];

    }

    package {
        'nginx':
            ensure => latest,
            require => File[ "/etc/yum.repos.d/nginx.repo" ];
    }
    
    file {
        
        "/etc/nginx/conf.d/default.conf":
            ensure => present,
            content => template("nginx/xbrowse_nginx.conf"),
            require => Package[ 'nginx' ],
            notify => Service[ 'nginx' ];
        
        "/etc/nginx/error-pages":
            ensure => directory,
            require => Package[ 'nginx' ],
            notify => Service[ 'nginx' ];

        "/etc/nginx/error-pages/500.html":
            ensure => present,
            source => "puppet:///modules/nginx/500.html",
            require => File[ '/etc/nginx/error-pages' ],
            notify => Service[ 'nginx' ];
        
        "/etc/nginx/error-pages/501.html":
            ensure => present,
            source => "puppet:///modules/nginx/501.html",
            require => File[ '/etc/nginx/error-pages' ],
            notify => Service[ 'nginx' ];
        
        "/etc/nginx/error-pages/502.html":
            ensure => present,
            source => "puppet:///modules/nginx/502.html",
            require => File[ '/etc/nginx/error-pages' ],
            notify => Service[ 'nginx' ];
        
        "/etc/nginx/error-pages/503.html":
            ensure => present,
            source => "puppet:///modules/nginx/503.html",
            require => File[ '/etc/nginx/error-pages' ],
            notify => Service[ 'nginx' ];
        
        "/etc/nginx/error-pages/maintenance.html":
            ensure => present,
            source => "puppet:///modules/nginx/maintenance.html",
            require => File[ '/etc/nginx/error-pages' ],
            notify => Service[ 'nginx' ];
        
    }
    
    service { 'nginx':
        require => Package[ 'nginx' ],
        ensure => running,
        hasstatus => true;
    }

}