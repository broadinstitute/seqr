FROM maven:latest

MAINTAINER MacArthur Lab

RUN apt-get update \
    && apt-get install -y xterm vim emacs

RUN git clone https://github.com/macarthur-lab/matchbox

WORKDIR matchbox

RUN mvn -Dmaven.test.skip=true clean install package

EXPOSE 9020

COPY entrypoint.sh .

CMD ["./entrypoint.sh"]

