#!/usr/bin/env python3
"""Assemble convenient third-party license/notice material for a release.

The complete corresponding-source archives remain authoritative.  This script
creates an additional, easy-to-consume bundle from license/copyright/notice
files already present in direct source material and generated source bundles.
It intentionally does not infer or relicense any component.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import tarfile
from pathlib import Path

LICENSE_NAME = re.compile(
    r"^(?:license|licence|copying|copyright|notice)(?:[._-].*)?$",
    re.IGNORECASE,
)
MAX_FILE_BYTES = 4 * 1024 * 1024


def safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", value)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--release-url", required=True)
    args = ap.parse_args()

    source_dir = Path(args.source_dir).resolve()
    output = Path(args.output).resolve()
    workspace = Path(args.workspace).resolve()
    output.mkdir(parents=True, exist_ok=True)

    bundle = workspace / "third-party-licenses"
    if bundle.exists():
        shutil.rmtree(bundle)
    files_dir = bundle / "files"
    files_dir.mkdir(parents=True)

    rows: list[list[str]] = []
    seen_digest: dict[str, str] = {}

    def store(origin_asset: str, origin_member: str, data: bytes) -> None:
        if not data or len(data) > MAX_FILE_BYTES:
            return
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen_digest:
            rows.append([origin_asset, origin_member, seen_digest[digest], digest, "duplicate"])
            return
        filename = f"{safe(origin_asset)}__{safe(origin_member)}"
        target = files_dir / filename
        counter = 1
        while target.exists():
            target = files_dir / f"{safe(origin_asset)}__{counter}__{safe(origin_member)}"
            counter += 1
        target.write_bytes(data)
        rel = target.relative_to(bundle).as_posix()
        seen_digest[digest] = rel
        rows.append([origin_asset, origin_member, rel, digest, "stored"])

    # Direct top-level license/copyright/notice assets.
    for path in sorted(source_dir.iterdir()):
        if not path.is_file():
            continue
        if (
            LICENSE_NAME.match(path.name)
            or path.name.startswith("LICENSE-")
            or path.name.startswith("COPYRIGHT-")
            or "-LICENSE-" in path.name
            or "-COPYRIGHT-" in path.name
        ):
            if path.stat().st_size <= MAX_FILE_BYTES:
                store(path.name, path.name, path.read_bytes())

    # Generated compliance archives expose dedicated license-material/ or
    # licenses/ directories.  Embedded-script archives also contain a GPL
    # license.  Read those members without extracting arbitrary archive paths.
    archive_candidates = [
        p
        for p in sorted(source_dir.glob("*.tar.gz"))
        if (
            "alpine-corresponding-source-" in p.name
            or p.name.endswith("cpan-corresponding-source.tar.gz")
            or p.name.endswith("s6-overlay-component-sources.tar.gz")
            or p.name.endswith("linuxserver-base-embedded-scripts.tar.gz")
        )
    ]
    for archive in archive_candidates:
        try:
            with tarfile.open(archive, "r:gz") as tf:
                for member in tf.getmembers():
                    if not member.isfile() or member.size > MAX_FILE_BYTES:
                        continue
                    parts = Path(member.name).parts
                    basename = Path(member.name).name
                    dedicated = "license-material" in parts or "licenses" in parts
                    embedded_license = (
                        archive.name.endswith("linuxserver-base-embedded-scripts.tar.gz")
                        and LICENSE_NAME.match(basename)
                    )
                    if not dedicated and not embedded_license:
                        continue
                    fh = tf.extractfile(member)
                    if fh is None:
                        continue
                    data = fh.read(MAX_FILE_BYTES + 1)
                    if len(data) <= MAX_FILE_BYTES:
                        store(archive.name, member.name, data)
        except tarfile.TarError as exc:
            raise SystemExit(f"Could not read compliance archive {archive}: {exc}") from exc

    if not rows:
        raise SystemExit("No license/copyright/notice material was collected")

    manifest = bundle / "THIRD_PARTY_LICENSES.tsv"
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["origin_asset", "origin_member", "bundled_file", "sha256", "status"])
        writer.writerows(rows)

    (bundle / "README.txt").write_text(
        "Third-party license and notice convenience bundle\n"
        "=================================================\n\n"
        "This bundle is generated from the exact source/compliance material for\n"
        "the container image. It is provided for convenient access to license,\n"
        "copyright, and notice files. It does not change any component's license\n"
        "and is not a substitute for the complete corresponding-source archives.\n\n"
        f"Complete compliance release: {args.release_url}\n",
        encoding="utf-8",
    )

    checksums = bundle / "SHA256SUMS"
    with checksums.open("w", encoding="utf-8") as fh:
        for path in sorted(bundle.rglob("*")):
            if path.is_file() and path != checksums:
                fh.write(f"{sha256(path)}  {path.relative_to(bundle).as_posix()}\n")

    archive = output / "third-party-licenses.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(bundle, arcname="third-party-licenses")
    shutil.copy2(manifest, output / "THIRD_PARTY_LICENSES.tsv")
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
