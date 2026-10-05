#!/usr/bin/env bash
# Add a workspace user to the manager group. Idempotent.
# Inputs: GROUP_NAME (from scripts.yml), GROUP_MEMBER (email; empty or unset
# means the identity running the script, so a plain bootstrap adds the deployer).
set -euo pipefail

member="${GROUP_MEMBER:-$(databricks current-user me -o json | jq -r .userName)}"

group_id=$(databricks groups list --filter "displayName eq \"$GROUP_NAME\"" -o json | jq -r '.[0].id // empty')
if [ -z "$group_id" ]; then
  echo "Group $GROUP_NAME not found. Run: databricks bundle run create_group -t <target>"
  exit 1
fi
user_id=$(databricks users list --filter "userName eq \"$member\"" -o json | jq -r '.[0].id // empty')
if [ -z "$user_id" ]; then
  echo "User $member not found in the workspace"
  exit 1
fi
if databricks groups get "$group_id" -o json | jq -e --arg id "$user_id" '.members[]? | select(.value == $id)' >/dev/null; then
  echo "$member is already a member of $GROUP_NAME"
  exit 0
fi
databricks groups patch "$group_id" --json "{
  \"schemas\": [\"urn:ietf:params:scim:api:messages:2.0:PatchOp\"],
  \"Operations\": [{\"op\": \"add\", \"path\": \"members\", \"value\": [{\"value\": \"$user_id\"}]}]
}"
echo "Added $member (id $user_id) to $GROUP_NAME (id $group_id)"
