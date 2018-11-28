#!/usr/bin/env bash

set +x
echo
echo "==== Installing mongo ===="
echo
set -x

if [ -z "$PLATFORM" ]; then
    set +x
    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    brew install mongodb

    mkdir -p /data/db
    sudo chown -R `id -un` /data/db

    mongod --fork --syslog

elif [ $PLATFORM = "centos" ]; then

    sudo tee /etc/yum.repos.d/mongodb-org-4.0.repo << EOM
[mongodb-org-4.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/4.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-4.0.asc
EOM

    sudo yum install update
    sudo yum install -y mongodb-org-4.0.3 mongodb-org-server-4.0.3 mongodb-org-shell-4.0.3 mongodb-org-mongos-4.0.3 mongodb-org-tools-4.0.3

    sudo service mongod start

elif [ $PLATFORM = "ubuntu" ]; then

    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
    echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.0.list
    sudo apt-get update

    sudo apt-get install -y mongodb-org=4.0.3 mongodb-org-server=4.0.3 mongodb-org-shell=4.0.3 mongodb-org-mongos=4.0.3 mongodb-org-tools=4.0.3

    sudo service mongod start

else
    set +x
    echo "Unexpected operating system: $PLATFORM"
    exit 1

fi;


set +x

echo Done