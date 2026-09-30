#!/usr/bin/env python3
"""Resolve LinuxServer.io's moving base-image tag to an immutable digest.

Only the first FROM instruction of the upstream docker-ddclient Dockerfile is
changed.  In addition to pinning the digest, this script resolves the exact
LinuxServer.io docker-baseimage-alpine source-release tag that corresponds to
the pulled base image and verifies that the tag exists upstream.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

BASE_IMAGE_REPOSITORY = "ghcr.io/linuxserver/baseimage-alpine"
BASE_SOURCE_REPOSITORY = "https://github.com/linuxserver/docker-baseimage-alpine.git"


def run(*args: str) -> str:
    proc = subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def repository_without_tag(ref: str) -> str:
    ref = ref.split("@", 1)[0]
    slash = ref.rfind("/")
    colon = ref.rfind(":")
    if colon > slash:
        return ref[:colon]
    return ref


def tag_from_reference(ref: str) -> str:
    ref = ref.split("@", 1)[0]
    slash = ref.rfind("/")
    colon = ref.rfind(":")
    if colon <= slash:
        raise SystemExit(f"Base image reference is not explicitly tagged: {ref}")
    tag = ref[colon + 1 :]
    if not tag or tag == "latest":
        raise SystemExit(f"Refusing non-specific base image tag: {ref}")
    return tag


def verified_base_release(base_ref: str, build_version: str) -> str:
    """Map LSIO's build_version label to the actual source release tag.

    linuxserver/baseimage-alpine images are referenced by a release line such as
    ``:3.22`` while their build_version label contains only the remote-change
    component, for example ``e8fd8152-ls30``.  The corresponding source tag is
    therefore ``3.22-e8fd8152-ls30``.  If upstream ever starts embedding the
    complete release tag in the label, keep it unchanged.
    """
    match = re.search(r"version:-\s*([^\s]+)", build_version)
    if not match:
        raise SystemExit(
            "Could not determine the LinuxServer.io base-image version from its build_version label"
        )

    label_version = match.group(1)
    release_line = tag_from_reference(base_ref)
    prefix = f"{release_line}-"
    base_release = label_version if label_version.startswith(prefix) else prefix + label_version

    try:
        result = run(
            "git",
            "ls-remote",
            "--exit-code",
            "--refs",
            BASE_SOURCE_REPOSITORY,
            f"refs/tags/{base_release}",
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"Could not verify LinuxServer.io base source tag {base_release!r} in "
            f"{BASE_SOURCE_REPOSITORY}"
        ) from exc

    if not result:
        raise SystemExit(
            f"LinuxServer.io base source tag {base_release!r} was not returned by upstream"
        )
    return base_release


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

    repo = repository_without_tag(base_ref)
    if repo != BASE_IMAGE_REPOSITORY:
        raise SystemExit(
            f"Unexpected LinuxServer.io base repository {repo!r}; expected {BASE_IMAGE_REPOSITORY!r}. "
            "The source collector must be reviewed before accepting a different base repository."
        )

    run("docker", "pull", base_ref)
    inspect = json.loads(run("docker", "image", "inspect", base_ref))[0]
    repo_digests = inspect.get("RepoDigests") or []

    digest_ref = next((d for d in repo_digests if d.startswith(repo + "@")), None)
    if digest_ref is None:
        raise SystemExit(
            f"Docker did not report a RepoDigest matching the requested base repository {repo} for {base_ref}; "
            f"reported values: {repo_digests!r}"
        )

    digest = digest_ref.split("@", 1)[1]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise SystemExit(f"Unexpected base image digest format: {digest!r}")
    pinned_ref = f"{repo}@{digest}"

    labels = (inspect.get("Config") or {}).get("Labels") or {}
    build_version = labels.get("build_version", "")
    base_release = verified_base_release(base_ref, build_version)

    newline = "\r\n" if lines[from_idx].endswith("\r\n") else "\n"
    prefix_match = re.match(r"^(\s*FROM\s+)", lines[from_idx], re.IGNORECASE)
    if prefix_match is None:
        raise SystemExit("Internal error while rewriting FROM instruction")
    lines[from_idx] = f"{prefix_match.group(1)}{pinned_ref}{from_suffix}{newline}"
    Path(args.output).write_text("".join(lines), encoding="utf-8")

    metadata = {
        "original_reference": base_ref,
        "repository": repo,
        "pinned_reference": pinned_ref,
        "digest": digest,
        "image_id": inspect.get("Id", ""),
        "build_version": build_version,
        "base_release": base_release,
        "base_source_repository": BASE_SOURCE_REPOSITORY,
    }
    Path(args.metadata).write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

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
