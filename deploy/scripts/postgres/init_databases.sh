${INSTALL_DIR}/postgres/pgsql/bin/initdb -D ${INSTALL_DIR}/postgres/datadir

${INSTALL_DIR}/postgres/pgsql/bin/pg_ctl -D ${INSTALL_DIR}/postgres/datadir  start

sleep 5   # wait for server to start

${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo drop database seqrdb)
${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo create database seqrdb)
${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo drop database xwiki)
${INSTALL_DIR}/postgres/pgsql/bin/psql postgres < <(echo create database xwiki)

${INSTALL_DIR}/postgres/pgsql/bin/pg_ctl -D ${INSTALL_DIR}/postgres/datadir  stop


