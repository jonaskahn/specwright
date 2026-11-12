#!/usr/bin/env python3
"""Generate the console's data contract (TypeScript types and JSON Schema) from dataformat.py.

The Python schema is the single source of truth. The output goes to console/contract/, which is
git-ignored in this repository and packed into the sw-view skill by console_pack.py.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "_shared" / "scripts"))

from kitlib import dataformat  # noqa: E402

OUT = ROOT / "console" / "contract"
WORDS = {
    "rows": "Row",
    "nodes": "Node",
    "edges": "Edge",
    "results": "Result",
    "findings": "Finding",
}


def ts_type(spec: str) -> str:
    base, nullable, values = dataformat.parse_type(spec)
    if base == "enum":
        inner = " | ".join(json.dumps(v) for v in values)
    elif base == "int":
        inner = "number"
    elif base == "bool":
        inner = "boolean"
    elif base == "[str]":
        inner = "string[]"
    else:
        inner = "string"
    return f"{inner} | null" if nullable else inner


def json_type(spec: str) -> dict:
    base, nullable, values = dataformat.parse_type(spec)
    if base == "enum":
        schema: dict = {"enum": [*values, None] if nullable else list(values)}
        return schema
    kinds = {"int": "integer", "bool": "boolean", "[str]": "array"}
    schema = {"type": kinds.get(base, "string")}
    if base == "[str]":
        schema["items"] = {"type": "string"}
    if base == "date":
        schema["pattern"] = r"^\d{4}-\d{2}-\d{2}"
    if nullable:
        schema = {"anyOf": [schema, {"type": "null"}]}
    return schema


def pascal(text: str) -> str:
    return text[:1].upper() + text[1:]


def typescript() -> str:
    lines = [
        "// Generated from skills/_shared/scripts/kitlib/dataformat.py. Do not edit.",
        "",
        f"export const FORMAT = {json.dumps(dataformat.FORMAT)};",
        f"export const FORMAT_VERSION = {dataformat.FORMAT_VERSION};",
        "",
        "export interface Envelope {",
        *(f"  {name}: {ts_type(spec)};" for name, spec in dataformat.ENVELOPE.items()),
        "}",
        "",
        "export interface IndexFile {",
        "  owner: string;",
        "  sha256: string;",
        "  bytes: number;",
        "  rows: number;",
        "  inputsDigest: string | null;",
        "}",
        "",
        "export interface DataIndex extends Envelope {",
        "  files: Record<string, IndexFile>;",
        "  idleAfterDays: number;",
        "  layout: string | null;",
        "  mode: string;",
        "  scopes: string[];",
        "  digest: string;",
        "}",
        "",
    ]
    names = []
    for kind, spec in sorted(dataformat.KINDS.items()):
        fields = []
        for list_name, row in spec.lists.items():
            row_name = f"{pascal(kind)}{WORDS.get(list_name, pascal(list_name))}"
            lines.append(f"export interface {row_name} {{")
            lines += [f"  {json.dumps(n)}: {ts_type(s)};" for n, s in row.items()]
            lines += ["}", ""]
            fields.append(f"  {list_name}: {row_name}[];")
        fields += [f"  {n}: {ts_type(s)};" for n, s in spec.top.items()]
        lines += [f"export interface {pascal(kind)}Data extends Envelope {{", *fields, "}", ""]
        names.append(kind)
    lines += [
        "export interface DataKinds {",
        *(f"  {k}: {pascal(k)}Data;" for k in names),
        "}",
        "",
        "export type KindName = keyof DataKinds;",
        "",
        "export const OWNERS: Record<string, string> = {",
        *(f"  {k}: {json.dumps(dataformat.KINDS[k].owner)}," for k in names),
        "};",
        "",
        f"export const RELATIONS = {json.dumps(list(dataformat.schema.RELATIONS))} as const;",
        "",
    ]
    return "\n".join(lines)


def json_schema() -> dict:
    defs: dict = {}
    for kind, spec in sorted(dataformat.KINDS.items()):
        props = {n: json_type(s) for n, s in dataformat.ENVELOPE.items()}
        for name, top in spec.top.items():
            props[name] = json_type(top)
        for name, row in spec.lists.items():
            props[name] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(row),
                    "properties": {n: json_type(s) for n, s in row.items()},
                },
            }
        defs[kind] = {
            "type": "object",
            "additionalProperties": False,
            "required": list(props),
            "properties": props,
        }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"{dataformat.FORMAT} {dataformat.FORMAT_VERSION}",
        "$defs": defs,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the files are not current")
    args = parser.parse_args(argv)
    files = {
        OUT / "types.ts": typescript(),
        OUT / "console-data.schema.json": json.dumps(json_schema(), indent=1) + "\n",
    }
    if args.check:
        return int(any(not p.is_file() or p.read_text() != text for p, text in files.items()))
    OUT.mkdir(parents=True, exist_ok=True)
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
