FROM redis:4.0.9

# utilities
RUN apt-get update && apt-get install -y lsof xterm vim emacs nano less

COPY bashrc /root/.bashrc

COPY redis.conf /usr/local/etc/redis/redis.conf

CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]