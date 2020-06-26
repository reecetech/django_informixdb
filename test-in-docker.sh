#!/bin/bash
set -euo pipefail

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

docker-compose -p ifx build

docker-compose -p ifx run test-runner tox
