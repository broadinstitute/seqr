FROM mongo:3.6.2

MAINTAINER MacArthur Lab

# install common utilities
RUN apt-get update && apt-get install -y --fix-missing \
    curl \
    less \
    wget

COPY bashrc /root/.bashrc
