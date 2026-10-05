#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: GROUP_MEMBER=<group_member_email> $0"
  echo
  echo "Creates the manager group and adds the given member to it."
  echo
  echo "Example: GROUP_MEMBER=user@example.com $0"
}

if [[ $# -ne 0 || -z "$GROUP_MEMBER" ]]; then
  usage
  exit 1
fi

databricks bundle run create_group -t prod --profile genie-prod-me
GROUP_MEMBER="$GROUP_MEMBER" databricks bundle run add_group_member -t prod --profile genie-prod-me