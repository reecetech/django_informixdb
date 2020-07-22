#!/bin/sh

set -euo pipefail

echo "* Checking Informix"
until $(nc -zv db 9088); do
    sleep 3
done
echo "* Informix available"
