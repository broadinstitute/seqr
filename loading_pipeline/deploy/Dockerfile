FROM --platform=linux/amd64 docker:dind as BUILD
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.11-alpine AS UV_BUILD
FROM --platform=linux/amd64 hailgenetics/hail:0.2.138-py3.11
COPY --from=BUILD /usr/local/bin/docker /usr/local/bin/docker
COPY --from=UV_BUILD /usr/local/bin/uv /usr/local/bin/uv
LABEL maintainer="Broad TGG"

RUN curl -sSL https://sdk.cloud.google.com | bash
ENV PATH $PATH:/root/google-cloud-sdk/bin

ARG PIPELINE_RUNNER_APP_VERSION
ENV PIPELINE_RUNNER_APP_VERSION=${PIPELINE_RUNNER_APP_VERSION}

ENV VIRTUAL_ENV="/.venv"

# Add build utilities for "annoy" package
# Note that these are getting added into the final runtime image and not the build...
# I (BPB) ran into challenges getting the uv virtual environment synced properly due
# to mismatches between the uv:python3.11-alpine and hail docker python environments.
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .
RUN uv sync --group prod --no-group dev --locked

# Application Code
WORKDIR /loading_pipeline
COPY loading_pipeline/api api
COPY loading_pipeline/bin bin
COPY loading_pipeline/lib lib
COPY loading_pipeline/ops ops
COPY loading_pipeline/var/liftover var/liftover

# Special paths
COPY loading_pipeline/var/spark_config/spark-defaults.conf /usr/local/lib/python3.10/dist-packages/pyspark/conf/spark-defaults.conf
COPY loading_pipeline/bin/vep /vep


WORKDIR /
EXPOSE 6000 8082
CMD ["uv", "run", "python3", "-m", "loading_pipeline.api"]
