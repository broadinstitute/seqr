#!/usr/bin/env bash

set +x
set +x
echo
echo "==== Installing postgres ===="
echo
set -x

if [ -z "$PLATFORM" ]; then
    set +x
    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    brew install postgres
    pg_ctl -D /usr/local/var/postgres start && brew services start postgresql

elif [ $PLATFORM = "centos" ]; then
    wget -nv https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-7-x86_64/pgdg-centos96-9.6-3.noarch.rpm
    sudo yum install -y pgdg-centos96-9.6-3.noarch.rpm epel-release

    sudo yum update -y
    sudo yum install -y postgresql96 postgresql96-server postgresql96-contrib
    sudo /usr/pgsql-9.6/bin/postgresql96-setup initdb

    PG_HBA_PATH=$(sudo find /var/lib/pgsql -name "pg_hba.conf")
    sudo sed -i s/peer/trust/  $PG_HBA_PATH
    sudo sed -i s/ident/trust/  $PG_HBA_PATH

    sudo systemctl stop postgresql-9.6   # make sure no postgres instance is running already
    sudo systemctl enable postgresql-9.6
    sudo systemctl start postgresql-9.6

elif [ $PLATFORM = "ubuntu" ]; then

    sudo apt-get install -y postgresql postgresql-contrib postgresql-client

    PG_HBA_PATH=$(find /etc/postgresql -name "pg_hba.conf")
    sudo sed -i s/peer/trust/ $PG_HBA_PATH
    sudo sed -i s/md5/trust/ $PG_HBA_PATH

    sudo systemctl stop postgresql
    sudo systemctl enable postgresql.service
    sudo systemctl start postgresql.service

else
    set +x
    echo "Unexpected operating system: $PLATFORM"
    exit 1

fi;

set +x

echo Done