#!/bin/bash
set -euo pipefail

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

export uniq_test_id="${uniq_test_id:-djifx}"

cleanup() {
    echo "--- cleaning up: previous code ${?}"
    docker compose -p "${uniq_test_id}" down --volumes --remove-orphans
}
trap cleanup EXIT

echo "--- building docker images"
docker compose -p "${uniq_test_id}" build

echo "--- starting dependencies"
docker compose -p "${uniq_test_id}" up -d db

echo "--- waiting for dependencies"
docker compose -p "${uniq_test_id}" run test-runner /usr/local/bin/wait-for-deps.sh

echo "--- running tests"
docker compose -p "${uniq_test_id}" run test-runner tox
