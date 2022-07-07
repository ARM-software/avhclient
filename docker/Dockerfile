# syntax=docker/dockerfile:1
FROM python:3.10.4-alpine3.15

LABEL org.opencontainers.image.source="https://github.com/ARM-software/avhclient"
LABEL org.opencontainers.image.base.name="python:3.10.4-alpine3.15"

RUN apk upgrade --no-cache && \
    apk add --no-cache bash git wget curl

ARG GIT_VERSION=main
RUN python3 -m pip install -U --no-cache-dir pip && \
    python3 -m pip install -U --no-cache-dir git+https://github.com/ARM-software/avhclient.git@$GIT_VERSION

CMD ["/bin/bash"]
