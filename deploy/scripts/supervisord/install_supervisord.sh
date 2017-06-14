set -x

export MY_PATH=$(dirname $(readlink -f "$0"))

sudo `which pip` install --upgrade supervisor

#mkdir -p supervisord && cd supervisord

# install the supervisord.conf
cat ${MY_PATH}/conf/supervisord.conf | \
    python -c "import sys; print sys.stdin.read().replace('%(INSTALL_DIR)s', '${INSTALL_DIR}')"  | \
    tee supervisord.conf

cp ${MY_PATH}/stop_supervisord.sh .
cp ${MY_PATH}/start_supervisord.sh .
