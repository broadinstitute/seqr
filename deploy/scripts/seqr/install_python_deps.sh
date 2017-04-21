curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo python;

sudo PATH=postgres/pgsql/bin/:$PATH \
   `which pip` install --upgrade -r seqr/requirements.txt;
