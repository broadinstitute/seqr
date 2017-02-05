${INSTALL_DIR}/postgres/pgsql/bin/initdb -D ${INSTALL_DIR}/postgres/datadir

${INSTALL_DIR}/postgres/pgsql/bin/pg_ctl -D ${INSTALL_DIR}/postgres/datadir  start

sleep 5   # wait for server to start

${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo CREATE USER seqr WITH SUPERUSER PASSWORD \'seqr\')   # create user in case it doesn't exist yet
${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo ALTER  USER seqr WITH SUPERUSER PASSWORD \'seqr\')   # if 'seqr' user already existed, just alter it
${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo CREATE USER xwiki WITH SUPERUSER PASSWORD \'xwiki\')   # create user in case it doesn't exist yet
${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo ALTER  USER xwiki WITH SUPERUSER PASSWORD \'xwiki\')   # if 'seqr' user already existed, just alter it
${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo CREATE USER postgres WITH SUPERUSER)   # create user in case it doesn't exist yet
${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo ALTER  USER postgres WITH SUPERUSER)   # if 'seqr' user already existed, just alter it

${INSTALL_DIR}/postgres/pgsql/bin/psql -U seqr postgres < <(echo drop database seqrdb)
${INSTALL_DIR}/postgres/pgsql/bin/psql -U seqr postgres < <(echo create database seqrdb)
${INSTALL_DIR}/postgres/pgsql/bin/psql -U seqr postgres < <(echo drop database xwiki)
${INSTALL_DIR}/postgres/pgsql/bin/psql -U seqr postgres < <(echo create database xwiki)

${INSTALL_DIR}/postgres/pgsql/bin/pg_ctl -D ${INSTALL_DIR}/postgres/datadir  stop


