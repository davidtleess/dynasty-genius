FROM mcr.microsoft.com/devcontainers/python:3.11

ARG DATABRICKS_CLI_VERSION=0.245.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip jq \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
