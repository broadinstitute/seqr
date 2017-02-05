set -x

mkdir -m 777 -p logs

mkdir -p postgres/datadir; chmod 700 postgres/datadir
mkdir -p mongo/datadir
