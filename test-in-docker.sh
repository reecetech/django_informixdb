#!/bin/bash
set -euo pipefail

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

if [[ -n "${TRAVIS:-}" ]] ; then
    export BUILDKIT_PROGRESS=plain
fi


travis_fold() {
    if [[ -n "${TRAVIS:-}" ]] ; then
        local action=$1
        local name=$2
        echo -en "travis_fold:${action}:${name}\r"
    fi
}

export uniq_test_id="${uniq_test_id:-djifx}"

cleanup() {
    travis_fold start cleaning
    echo "--- cleaning up: previous code ${?}"
    docker-compose -p "${uniq_test_id}" down --volumes --remove-orphans
    travis_fold end cleaning
}
trap cleanup EXIT

travis_fold start building
echo "--- building docker images"
docker-compose -p "${uniq_test_id}" build
travis_fold end building

travis_fold start dependencies
echo "--- starting dependencies"
docker-compose -p "${uniq_test_id}" up -d db

echo "--- waiting for dependencies"
docker-compose -p "${uniq_test_id}" run test-runner /usr/local/bin/wait-for-deps.sh
travis_fold end dependencies

echo "--- running tests"
docker-compose -p "${uniq_test_id}" run test-runner tox
