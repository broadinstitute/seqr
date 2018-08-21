FROM redis:4.0.9

MAINTAINER MacArthur Lab

# install commmon utilities
RUN apt-get update && apt-get install -y --fix-missing \
    curl \
    less \
    wget

COPY bashrc /root/.bashrc

COPY redis.conf /usr/local/etc/redis/redis.conf

CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]