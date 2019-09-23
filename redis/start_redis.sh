cd /Users/zhuang/code/seqr/redis
LOG_FILE=$(pwd)/redis.log
(nohup redis-server ${SEQR_DIR}/deploy/docker/redis/redis.conf >& ${LOG_FILE}) &
echo "redis started in background on port 6379. See ${LOG_FILE}"

