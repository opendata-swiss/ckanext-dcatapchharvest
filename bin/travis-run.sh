#!/bin/bash

set -e

function cleanup {
    exit $?
}

trap "cleanup" EXIT

# Check PEP-8 code style and McCabe complexity
flake8 --statistics --show-source ckanext --ignore=E122,E501,E123

# Tests will be added in the next step
