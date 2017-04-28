FROM maven:latest

MAINTAINER MacArthur Lab

# utilities
RUN apt-get update
RUN apt-get install -y xterm vim emacs nano

RUN git clone https://github.com/macarthur-lab/matchbox

WORKDIR matchbox

RUN mvn -Dmaven.test.skip=true clean install package

EXPOSE 9020

COPY bashrc /root/.bashrc

COPY entrypoint.sh .

CMD ["./entrypoint.sh"]

