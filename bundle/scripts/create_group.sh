#!/usr/bin/env bash
# Create the manager group if it does not exist. Idempotent.
# Input: GROUP_NAME (set by scripts.yml from the bundle variable).
set -euo pipefail

existing=$(databricks groups list --filter "displayName eq \"$GROUP_NAME\"" -o json | jq -r '.[0].id // empty')
if [ -n "$existing" ]; then
  echo "Group $GROUP_NAME already exists (id $existing)"
  exit 0
fi
databricks groups create --display-name "$GROUP_NAME" -o json | jq -r '"Created group \(.displayName) (id \(.id))"'
