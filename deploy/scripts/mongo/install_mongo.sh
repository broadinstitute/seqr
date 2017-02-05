set -x

export MY_PATH=$(dirname $(readlink -f "$0"))

mkdir -p mongo && cd mongo

wget -c -N https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-rhel70-3.4.1.tgz -O mongodb-linux-x86_64-rhel70-3.4.1.tgz  && tar xzf mongodb*.tgz

cat ${MY_PATH}/conf/mongod.conf | \
    python -c "import sys; print sys.stdin.read().replace('\${INSTALL_DIR}', '${INSTALL_DIR}')"  | \
    tee mongod.conf
