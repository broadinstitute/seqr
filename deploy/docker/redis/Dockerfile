FROM redis:6.0.6

LABEL maintainer="Broad TGG"

COPY bashrc /root/.bashrc

COPY redis.conf /usr/local/etc/redis/redis.conf

CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]