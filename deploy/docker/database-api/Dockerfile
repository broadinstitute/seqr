FROM openjdk:8-jdk

RUN cd /usr/local \
    && wget -nv http://d3kbcqa49mib13.cloudfront.net/spark-2.0.2-bin-hadoop2.7.tgz \
    && tar xzf /usr/local/spark-2.0.2-bin-hadoop2.7.tgz

RUN apt-get update && apt-get install -y g++ cmake python-pip python-dev

RUN git clone https://github.com/cseed/hail.git \
    && cd hail \
    && git checkout seqr2 \
    && ls

# && ./gradlew -Dspark.version=2.0.2 shadowJar archiveZip   # <--- this doesn't work because of solr jar version conflicts
RUN cd /hail \
    && ./gradlew -Dspark.version=2.0.2 installDist \
    && rm ./build/install/hail/lib/asm-3.1.jar



RUN pip install --upgrade pip
RUN pip install --upgrade decorator numpy ipython

COPY bashrc /root/.bashrc

COPY seqrserver.py /
COPY entrypoint.sh /

WORKDIR /

CMD [ "/entrypoint.sh" ]
