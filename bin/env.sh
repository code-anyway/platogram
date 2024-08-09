#!/usr/bin/env bash
set -a
source <(grep -v '^#' .env | sed -e 's/^/export /')
set +a