##2014-11-25 - Release 0.9.0
###Summary

This release has a number of new parameters, support for 2.6, improved providers, and several bugfixes.

####Features
- New parameters: `mongodb::globals`
  - `$service_ensure`
  - `$service_enable`
- New parameters: `mongodb`
  - `$quiet`
- New parameters: `mongodb::server`
  - `$service_ensure`
  - `$service_enable`
  - `$quiet`
  - `$config_content`
- Support for mongodb 2.6
- Reimplement `mongodb_user` and `mongodb_database` provider
- Added `mongodb_conn_validator` type

####Bugfixes
- Use hkp for the apt keyserver
- Fix mongodb database existance check
- Fix `$server_package_name` problem (MODULES-690)
- Make sure `pidfilepath` doesn't have any spaces
- Providers need the client command before they can work (MODULES-1285)

##2014-05-27 - Release 0.8.0
###Summary

This feature features a rewritten mongodb_replset{} provider, includes several
important bugfixes, ruby 1.8 support, and two new features.

####Features
- Rewritten mongodb_replset{}, featuring puppet resource support, prefetching,
and flushing.
- Add Ruby 1.8 compatibility.
- Adds `syslog`, allowing you to configure mongodb to send all logging to the hosts syslog.
- Add mongodb::replset, a wrapper class for hiera users.
- Improved testing!

####Bugfixes
- Fixes the package names to work since 10gen renamed them again.
- Fix provider name in the README.
- Disallow `nojournal` and `journal` to be set at the same time.
- Changed - to = for versioned install on Ubuntu.

##2014-1-29 - Release 0.7.0
###Summary

Added Replica Set Type and Provider

##2014-1-17 - Release 0.6.0
###Summary

Added support for installing MongoDB client on 
RHEL family systems.

##2014-01-10 Release 0.5.0
###Summary

Added types for providers for Mongo users and databases.

##2013-12 Release 0.4.0

Major refactoring of the MongoDB module. Includes a new 'mongodb::globals' 
that consolidates many shared parameters into one location. This is an 
API-breaking release in anticipation of a 1.0 release.

##2013-10-31 - Release 0.3.0
###Summary

Adds a number of parameters and fixes some platform
specific bugs in module deployment.

##2013-09-25 - Release 0.2.0
###Summary

This release fixes a duplicate parameter.

####Bugfixes
- Fix a duplicated parameter.

##2012-07-13 - Release 0.1.0
- Add support for RHEL/CentOS
- Change default mongodb install location to OS repo

##2012-05-29 - Release 0.0.2
- Fix Modulefile typo.
- Remove repo pin.
- Update spec tests and add travis support.

##2012-05-03 - Release 0.0.1
- Initial Release.
