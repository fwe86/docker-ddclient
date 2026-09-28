#!/usr/bin/env python3
"""Resolve the moving LinuxServer.io base-image tag to an immutable digest.

The script intentionally changes only the first FROM instruction of an upstream
Dockerfile.  The original Dockerfile remains part of the compliance bundle.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def run(*args: str) -> str:
    proc = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stdout.strip()


def repository_without_tag(ref: str) -> str:
    ref = ref.split("@", 1)[0]
    slash = ref.rfind("/")
    colon = ref.rfind(":")
    if colon > slash:
        return ref[:colon]
    return ref


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dockerfile", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--github-env")
    args = ap.parse_args()

    src = Path(args.dockerfile).read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)

    from_idx = None
    base_ref = None
    from_suffix = ""
    pat = re.compile(r"^(\s*FROM\s+)(\S+)(.*)$", re.IGNORECASE)
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        m = pat.match(line.rstrip("\r\n"))
        if m:
            from_idx = idx
            base_ref = m.group(2)
            from_suffix = m.group(3)
            break

    if from_idx is None or not base_ref:
        raise SystemExit("No FROM instruction found")
    if "$" in base_ref:
        raise SystemExit(f"Refusing unresolved FROM expression: {base_ref}")

    run("docker", "pull", base_ref)
    inspect = json.loads(run("docker", "image", "inspect", base_ref))[0]
    repo_digests = inspect.get("RepoDigests") or []
    repo = repository_without_tag(base_ref)

    digest_ref = next((d for d in repo_digests if d.startswith(repo + "@")), None)
    if digest_ref is None:
        raise SystemExit(
            f"Docker did not report a RepoDigest matching the requested base repository {repo} for {base_ref}; "
            f"reported values: {repo_digests!r}"
        )

    digest = digest_ref.split("@", 1)[1]
    pinned_ref = f"{repo}@{digest}"

    newline = "\r\n" if lines[from_idx].endswith("\r\n") else "\n"
    prefix = re.match(r"^(\s*FROM\s+)", lines[from_idx], re.IGNORECASE).group(1)  # type: ignore[union-attr]
    lines[from_idx] = f"{prefix}{pinned_ref}{from_suffix}{newline}"
    Path(args.output).write_text("".join(lines), encoding="utf-8")

    labels = (inspect.get("Config") or {}).get("Labels") or {}
    build_version = labels.get("build_version", "")
    match = re.search(r"version:-\s*([^\s]+)", build_version)
    if not match:
        raise SystemExit(
            "Could not determine the LinuxServer.io base-image release from its build_version label"
        )
    base_release = match.group(1)

    metadata = {
        "original_reference": base_ref,
        "repository": repo,
        "pinned_reference": pinned_ref,
        "digest": digest,
        "image_id": inspect.get("Id", ""),
        "build_version": build_version,
        "base_release": base_release,
    }
    Path(args.metadata).write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.github_env:
        with Path(args.github_env).open("a", encoding="utf-8") as fh:
            fh.write(f"LSIO_BASE_IMAGE={base_ref}\n")
            fh.write(f"LSIO_BASE_DIGEST={digest}\n")
            fh.write(f"LSIO_BASE_PINNED={pinned_ref}\n")
            fh.write(f"LSIO_BASE_RELEASE={base_release}\n")

    print(pinned_ref)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
