FROM maven:latest

MAINTAINER MacArthur Lab

RUN git clone https://github.com/macarthur-lab/matchbox

WORKDIR matchbox

RUN mvn -Dmaven.test.skip=true clean install package

COPY application.properties resources/

COPY entrypoint.sh .

CMD ["./entrypoint.sh"]
