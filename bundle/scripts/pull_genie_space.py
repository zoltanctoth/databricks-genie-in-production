"""Pull a deployed Genie Agent's configuration back into its bundle YAML.

Curation happens in the Genie UI; a deploy overwrites the space with the YAML. Run
this after every UI change so the change lands in git before the next
deploy:

    uv run bundle/scripts/pull_genie_space.py market_analyst -t dev --profile <profile>

It asks `bundle summary` for the target's space ID, catalog and schema (bundle
scripts cannot read resource fields such as space_id), reads the space through the
API, turns the literal table names back into
${var.catalog}.${resources.schemas.schema.name}, and replaces the
`serialized_space: |` block in resources/<key>.genie_space.yml. It writes only that
block, so title and description stay as they are in the YAML.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CATALOG_VAR = "${var.catalog}"
SCHEMA_VAR = "${resources.schemas.schema.name}"


def databricks(*args: str) -> dict:
    out = subprocess.run(["databricks", *args, "-o", "json"], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def target_values(key: str, target: str, profile: str) -> tuple[str, str, str]:
    resources = databricks("bundle", "summary", "-t", target, "--profile", profile)["resources"]
    space = resources.get("genie_spaces", {}).get(key)
    if not space or not space.get("id"):
        sys.exit(f"Genie space '{key}' is not deployed in target '{target}'; run bundle deploy first.")
    schema = resources["schemas"]["schema"]
    return space["id"], schema["catalog_name"], schema["name"]


def fetch_serialized_space(space_id: str, profile: str) -> dict:
    space = databricks("genie", "get-space", space_id, "--include-serialized-space", "--profile", profile)
    if not space.get("serialized_space"):
        sys.exit(f"Space {space_id} returned no serialized_space; CAN_EDIT on the space is required.")
    return json.loads(space["serialized_space"])


def tokenize(text: str, catalog: str, schema: str) -> str:
    # Plain names in identifiers, backticked names in SQL that Genie writes.
    text = text.replace(f"{catalog}.{schema}.", f"{CATALOG_VAR}.{SCHEMA_VAR}.")
    text = text.replace(f"`{catalog}`.`{schema}`.", f"`{CATALOG_VAR}`.`{SCHEMA_VAR}`.")
    if re.search(rf"\b{re.escape(schema)}\b", text):
        sys.exit(f"'{schema}' still appears after replacing the qualified names; fix it by hand in the UI or the YAML.")
    return text


def replace_block(yaml_text: str, body: str) -> str:
    lines = yaml_text.splitlines(keepends=True)
    starts = [i for i, l in enumerate(lines) if re.match(r"^\s*serialized_space: \|\s*$", l)]
    if len(starts) != 1:
        sys.exit(f"Expected one 'serialized_space: |' line, found {len(starts)}.")
    start = starts[0]
    indent = " " * (len(lines[start]) - len(lines[start].lstrip()) + 2)
    end = start + 1
    while end < len(lines) and (lines[end].startswith(indent) or not lines[end].strip()):
        end += 1
    block = [indent + l + "\n" for l in body.splitlines()]
    return "".join(lines[: start + 1] + block + lines[end:])


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull a Genie space's UI changes into its bundle YAML.")
    parser.add_argument("key", help="resource key under genie_spaces, e.g. market_analyst")
    parser.add_argument("-t", "--target", default="dev")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parent.parent)  # bundle root, so it runs from any folder
    resource_file = f"resources/{args.key}.genie_space.yml"

    space_id, catalog, schema = target_values(args.key, args.target, args.profile)
    space = fetch_serialized_space(space_id, args.profile)
    body = tokenize(json.dumps(space, indent=2, sort_keys=True), catalog, schema)

    with open(resource_file) as f:
        old = f.read()
    new = replace_block(old, body)
    if new == old:
        print(f"{resource_file}: already up to date with space {space_id}.")
        return
    with open(resource_file, "w") as f:
        f.write(new)
    print(f"{resource_file}: serialized_space updated from space {space_id}. Review with git diff.")


if __name__ == "__main__":
    main()
