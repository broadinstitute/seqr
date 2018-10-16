#!/usr/bin/env bash

export PT_VERSION="1.2.6"
wget https://nexus.phenotips.org/nexus/content/repositories/releases/org/phenotips/phenotips-standalone/${PT_VERSION}/phenotips-standalone-${PT_VERSION}.zip \
    && unzip phenotips-standalone-${PT_VERSION}.zip \
    && rm phenotips-standalone-${PT_VERSION}.zip

cd phenotips-standalone-${PT_VERSION}
wget https://jdbc.postgresql.org/download/postgresql-42.1.4.jar -O ./webapps/phenotips/WEB-INF/lib/postgresql-42.1.4.jar

cp ${SEQR_DIR}/deploy/docker/phenotips/config/${PT_VERSION}/xwiki.cfg ./webapps/phenotips/WEB-INF/xwiki.cfg
cp ${SEQR_DIR}/deploy/docker/phenotips/config/${PT_VERSION}/hibernate.cfg.xml ./webapps/phenotips/WEB-INF/hibernate.cfg.xml
sed -i 's/<property.name="connection.url">.*<\/property>/<property name="connection.url">jdbc:postgresql:\/\/localhost:5432\/xwiki<\/property>/' ./webapps/phenotips/WEB-INF/hibernate.cfg.xml

rm -rf data/extension data/jobs
cp -r ${SEQR_DIR}/deploy/docker/phenotips/init/${PT_VERSION}/extension ./data/extension
cp -r ${SEQR_DIR}/deploy/docker/phenotips/init/${PT_VERSION}/jobs ./data/jobs

# init PhenoTips db
psql -U postgres postgres -c "create role xwiki with CREATEDB LOGIN PASSWORD 'xwiki'"
psql -U postgres postgres -c 'grant all privileges on database xwiki to xwiki'
psql -U xwiki postgres -c 'create database xwiki'
psql -U xwiki xwiki -f ${SEQR_DIR}/deploy/docker/phenotips/init/${PT_VERSION}/init_phenotips_db.sql

./start.sh &
