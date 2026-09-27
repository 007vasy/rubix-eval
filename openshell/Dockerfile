# syntax=docker/dockerfile:1
# Build on the host (has internet), then create an OpenShell sandbox from the image
# with openshell/policy.yaml (no public internet).
#
#   DOCKER_HOST=unix:///var/run/docker.sock docker build -f openshell/Dockerfile -t rubix-eval-verified:local .
#   openshell sandbox create --name rubix-eval --from rubix-eval-verified:local --policy ./openshell/policy.yaml --no-auto-providers --detach

FROM ghcr.io/nvidia/openshell-community/sandboxes/base:latest

USER root
ENV DEBIAN_FRONTEND=noninteractive \
    RUBIX_LANE=verified \
    RUBIX_WEB_ACCESS=0 \
    RUBIX_HARNESS=openshell \
    RUBIX_TRUSTED_RENDERER=0 \
    RUBIX_SOLVES_DIR=/eval/solves \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb \
        fonts-liberation \
        wget \
        ca-certificates \
    && wget -qO /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y --no-install-recommends /tmp/chrome.deb \
    && rm -f /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/rubix-eval
COPY pyproject.toml README.md LICENSE /opt/rubix-eval/
COPY src /opt/rubix-eval/src
COPY web /opt/rubix-eval/web
COPY evals /opt/rubix-eval/evals
COPY docs /opt/rubix-eval/docs
COPY openshell/skills /sandbox/.agents/skills
COPY openshell/run-verified.sh /usr/local/bin/run-verified
COPY openshell/policy.yaml /etc/openshell/policy.yaml

RUN chmod +x /usr/local/bin/run-verified \
    && mkdir -p /sandbox/.claude/skills /eval /eval/solves \
    && ln -sf /sandbox/.agents/skills/rubiks-eval /sandbox/.claude/skills/rubiks-eval \
    && /sandbox/.venv/bin/pip install --no-cache-dir /opt/rubix-eval \
    && chown -R sandbox:sandbox /opt/rubix-eval /eval /sandbox/.agents /sandbox/.claude /sandbox/.venv

USER sandbox
WORKDIR /eval
