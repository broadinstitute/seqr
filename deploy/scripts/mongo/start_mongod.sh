nohup ${INSTALL_DIR}/mongo/mongodb-*/bin/mongod -f ${INSTALL_DIR}/mongo/mongod.conf >& ${INSTALL_DIR}/logs/mongod.log & 
# less +F ${INSTALL_DIR}/logs/mongod.log
