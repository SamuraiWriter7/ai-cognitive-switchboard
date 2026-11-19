#!/usr/bin/env python3
"""Check the three v0.1 fixtures against the Schema and record-local rules.

Run: python scripts/validate.py
Dependency: python -m pip install "jsonschema>=4.18,<5"

Exit codes: 0 = expectations met, 1 = mismatch, 2 = input/setup error.
History, external evidence, fixed-policy decisions and runtime are unverified.
"""

from datetime import datetime
import json
from pathlib import Path
import sys

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError:
    print('Missing dependency. Run: python -m pip install "jsonschema>=4.18,<5"', file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "switchboard-v0.1.schema.json"
CASES = (
    ("examples/valid-switch.json", "active", "PASS"),
    ("examples/denied-switch.json", "denied", "PASS"),
    ("examples/unauthorized-activation.json", "active", "FAIL"),
)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )


def semantic_errors(record):
    """Run only after structural validation has passed."""
    errors = []
    authorization = record["authorization"]
    review = record["human_review"]
    approved = record["authorized_state"]
    review_required = record["human_review_required"]

    timestamps = {key: record[key] for key in ("created_at", "expires_at", "activated_at")}
    if authorization is not None:
        timestamps["authorized_at"] = authorization["authorized_at"]
        timestamps["authorization.valid_until"] = authorization["valid_until"]
    if review is not None:
        timestamps["reviewed_at"] = review["reviewed_at"]
        timestamps["human_review.valid_until"] = review["valid_until"]

    times = {}
    for key, value in timestamps.items():
        if value is not None:
            try:
                times[key] = datetime.fromisoformat(value[:-1] + "+00:00")
            except ValueError:
                errors.append(f"{key}: invalid calendar date or time")

    if not errors:
        created, expires = times["created_at"], times["expires_at"]
        if not created < expires:
            errors.append("expected created_at < expires_at")
        if authorization is not None:
            authorized = times["authorized_at"]
            if not created <= authorized < expires <= times["authorization.valid_until"]:
                errors.append("expected created_at <= authorized_at < expires_at <= authorization.valid_until")
            if record["status"] == "active" and not authorized <= times["activated_at"] < expires:
                errors.append("expected authorized_at <= activated_at < expires_at")
            if review_required and record["status"] in {"authorized", "active"}:
                if not created <= times["reviewed_at"] <= authorized < expires <= times["human_review.valid_until"]:
                    errors.append("required review must precede or coincide with authorization and cover the record's lifetime")

    if record["supersedes_ref"] == record["record_id"]:
        errors.append("supersedes_ref must not reference the record itself")
    if record["status"] == "active" and record["effective_state"] != approved:
        errors.append("effective_state must exactly match authorized_state")
    if record["requested_state"]["human_review_required"] and not review_required:
        errors.append("a required human review cannot be relaxed")

    if approved is not None:
        if approved["human_review_required"] != review_required:
            errors.append("authorized_state.human_review_required must match the record")
        required_bindings = {
            "mode_profile_ref": True,
            "memory_ref": approved["memory"] != "OFF",
            "external_brain_ref": approved["external_brain"] == "ON",
            "question_pack_ref": approved["question_pack"] is not None,
        }
        scoped_refs = set(record["scope"]["resource_refs"])
        for field, required in required_bindings.items():
            ref = record["bindings"][field]
            if required and ref is None:
                errors.append(f"bindings.{field}: reference required by authorized_state")
            elif not required and ref is not None:
                errors.append(f"bindings.{field}: must be null for authorized_state")
            if ref is not None and ref not in scoped_refs:
                errors.append(f"bindings.{field}: reference not in scope.resource_refs")

    return errors


def check_fixture(validator, filename, status, expected):
    record = load_json(ROOT / filename)
    if not isinstance(record, dict) or record.get("status") != status:
        print(f"[MISMATCH] {filename} expected fixture status={status}")
        return False

    structure = list(validator.iter_errors(record))
    semantic = semantic_errors(record) if not structure else None
    actual = "FAIL" if structure or semantic else "PASS"

    if expected == "FAIL":
        signature = [(tuple(err.absolute_path), err.validator) for err in structure]
        matches = signature == [(("authorization",), "type")]
    else:
        matches = actual == expected

    label = "MATCH" if matches else "MISMATCH"
    structure_label = "FAIL" if structure else "PASS"
    semantic_label = "SKIP" if semantic is None else ("FAIL" if semantic else "PASS")
    print(f"[{label}] {filename} expected={expected} actual={actual} "
          f"structure={structure_label} record_semantics={semantic_label}")
    for err in structure:
        path = "/" + "/".join(str(part) for part in err.absolute_path)
        print(f"  {path}: {err.message}")
    for err in semantic or ():
        print(f"  {err}")

    return matches


def main():
    try:
        schema = load_json(SCHEMA)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        results = [check_fixture(validator, *case) for case in CASES]
    except (OSError, ValueError, SchemaError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    print(f"Fixture expectations matched: {sum(results)}/{len(results)}")
    print("Lifecycle transitions, external evidence and runtime: UNVERIFIED")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
