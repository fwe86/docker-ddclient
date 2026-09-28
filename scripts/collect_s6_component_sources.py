#!/usr/bin/env python3
"""Archive exact sources for the binary components bundled by s6-overlay.

s6-overlay's conf/versions file records the exact tag/commit used for BearSSL,
the skarnet stack, and s6-overlay-helpers.  This collector follows those exact
references and preserves source plus upstream license/copyright files.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

COMPONENTS = {
    "BEARSSL": ("BearSSL", "https://www.bearssl.org/git/BearSSL"),
    "SKALIBS": ("skalibs", "https://github.com/skarnet/skalibs.git"),
    "EXECLINE": ("execline", "https://github.com/skarnet/execline.git"),
    "S6": ("s6", "https://github.com/skarnet/s6.git"),
    "S6_RC": ("s6-rc", "https://github.com/skarnet/s6-rc.git"),
    "S6_LINUX_INIT": ("s6-linux-init", "https://github.com/skarnet/s6-linux-init.git"),
    "S6_PORTABLE_UTILS": ("s6-portable-utils", "https://github.com/skarnet/s6-portable-utils.git"),
    "S6_LINUX_UTILS": ("s6-linux-utils", "https://github.com/skarnet/s6-linux-utils.git"),
    "S6_DNS": ("s6-dns", "https://github.com/skarnet/s6-dns.git"),
    "S6_NETWORKING": ("s6-networking", "https://github.com/skarnet/s6-networking.git"),
    "S6_OVERLAY_HELPERS": ("s6-overlay-helpers", "https://github.com/just-containers/s6-overlay-helpers.git"),
}
LICENSE_NAMES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt", "COPYRIGHT", "NOTICE")


def run(args: list[str], *, cwd: Path | None = None, capture: bool = True) -> str:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return proc.stdout.strip() if capture and proc.stdout is not None else ""


def parse_versions(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", value)


def checkout_ref(url: str, ref: str, dest: Path) -> str:
    # Full clone is deliberate: it also works for BearSSL commit references and
    # avoids depending on servers permitting shallow fetches of unadvertised SHAs.
    run(["git", "clone", "-q", url, str(dest)], capture=False)
    proc = subprocess.run(
        ["git", "-C", str(dest), "checkout", "-q", ref],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        # Some mirrors do not materialize all tags in a normal clone. Try an
        # explicit fetch before failing closed.
        run(["git", "-C", str(dest), "fetch", "-q", "origin", ref], capture=False)
        run(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"], capture=False)
    return run(["git", "-C", str(dest), "rev-parse", "HEAD"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s6-repo", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()

    s6_repo = Path(args.s6_repo).resolve()
    output = Path(args.output).resolve()
    workspace = Path(args.workspace).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    versions_file = s6_repo / "conf" / "versions"
    if not versions_file.is_file():
        raise SystemExit(f"s6-overlay conf/versions not found: {versions_file}")
    versions = parse_versions(versions_file)

    bundle = workspace / "s6-component-sources"
    archives = bundle / "sources"
    licenses = bundle / "licenses"
    repos = workspace / "repos"
    archives.mkdir(parents=True)
    licenses.mkdir()
    repos.mkdir()

    rows: list[list[str]] = []
    for key, (name, url) in COMPONENTS.items():
        version_key = f"{key}_VERSION"
        ref = versions.get(version_key)
        if not ref:
            raise SystemExit(f"Missing {version_key} in {versions_file}")

        repo = repos / name
        commit = checkout_ref(url, ref, repo)
        archive_name = f"{safe(name)}-{safe(ref)}.tar.gz"
        run(
            [
                "git",
                "-C",
                str(repo),
                "archive",
                "--format=tar.gz",
                f"--prefix={name}-{ref}/",
                f"--output={archives / archive_name}",
                commit,
            ],
            capture=False,
        )

        found: list[str] = []
        for candidate in LICENSE_NAMES:
            src = repo / candidate
            if src.is_file():
                target = licenses / f"{safe(name)}-{candidate}"
                shutil.copy2(src, target)
                found.append(target.name)
        if not found:
            raise SystemExit(f"No license/copyright file found for s6 component {name} at {ref}")

        rows.append([name, ref, commit, url, f"sources/{archive_name}", ",".join(found)])

    manifest = bundle / "S6_COMPONENTS.tsv"
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["component", "upstream_ref", "commit", "repository", "source_archive", "license_files"])
        writer.writerows(rows)

    archive = output / "s6-overlay-component-sources.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(bundle, arcname="s6-overlay-component-sources")
    shutil.copy2(manifest, output / "S6_COMPONENTS.tsv")

    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
