FROM hailgenetics/hail:0.2.128

LABEL maintainer="Broad TGG"

RUN pip install --no-cache-dir clickhouse-connect==0.8.18

WORKDIR /vlm

# Application Code
COPY vlm/ .

WORKDIR /
EXPOSE 7000
CMD ["python3", "-m", "vlm"]
