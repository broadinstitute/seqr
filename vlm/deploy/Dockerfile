FROM python:3.11-slim-bullseye

LABEL maintainer="Broad TGG"

WORKDIR /vlm

RUN pip install --no-cache-dir -r requirements.txt

# Application Code
COPY vlm/ .

WORKDIR /
EXPOSE 7000
CMD ["python3", "-m", "vlm"]
