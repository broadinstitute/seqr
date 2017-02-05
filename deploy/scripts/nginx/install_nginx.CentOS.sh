set -x

export MY_PATH=$(dirname $(readlink -f "$0"))

cd $INSTALL_DIR

mkdir -p logs/nginx
mkdir -p nginx && cd nginx

# https://www.nginx.com/resources/wiki/start/topics/tutorials/install/#prebuilt-packages-for-linux-and-bsd

echo '[nginx]
name=nginx repo
baseurl=http://nginx.org/packages/centos/$releasever/$basearch/
gpgcheck=0
enabled=1
' | sudo tee /etc/yum.repos.d/nginx.repo

sudo yum install -y nginx

# install the nginx.conf
cat ${MY_PATH}/conf/nginx.conf | \
    python -c "import sys; print sys.stdin.read().replace('\${INSTALL_DIR}', '${INSTALL_DIR}').replace('\${SERVER_URL}', '${SERVER_URL}').replace('\${SSL_CERTIFICATE_PEM_FILE_PATH}', '${SSL_CERTIFICATE_PEM_FILE_PATH}').replace('\${SSL_CERTIFICATE_KEY_FILE_PATH}', '${SSL_CERTIFICATE_KEY_FILE_PATH}')"  | \
    sudo tee /etc/nginx/nginx.conf

# copy key files
cp ${MY_PATH}/keys/*.key .
cp ${MY_PATH}/keys/*.pem .

sudo service nginx restart
