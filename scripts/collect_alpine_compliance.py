#!/usr/bin/env python3
"""Collect exact Alpine package metadata and corresponding source inputs.

The final container image is authoritative: every installed APK package is
included, not merely packages guessed from a Dockerfile or an SBOM scanner.
For each unique Alpine source package/commit the exact aports directory is
archived and `abuild fetch` downloads/checks the remote source inputs.

The script fails closed.  Missing commit provenance, missing APKBUILD files, or
source-fetch/checksum errors abort the build before any image is published.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
import re
from collections import OrderedDict
from pathlib import Path

APORTS_REMOTE = "https://gitlab.alpinelinux.org/alpine/aports.git"
REPOSITORIES = ("main", "community", "testing")

LICENSE_BASENAME = re.compile(r"^(?:license|licence|copying|copyright|notice)(?:[._-].*)?$", re.IGNORECASE)
MAX_LICENSE_BYTES = 2 * 1024 * 1024


def _safe_fragment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", value)


def collect_license_material(source: Path, destination: Path, prefix: str) -> list[str]:
    """Extract only small license/notice files from a source archive.

    This is supplementary convenience material. The complete source archive is
    still retained regardless of whether a conventional license filename exists.
    """
    collected: list[str] = []
    destination.mkdir(parents=True, exist_ok=True)

    def store(name: str, data: bytes) -> None:
        if len(data) > MAX_LICENSE_BYTES:
            return
        target = destination / f"{_safe_fragment(prefix)}__{_safe_fragment(name)}"
        counter = 1
        while target.exists():
            target = destination / f"{_safe_fragment(prefix)}__{counter}__{_safe_fragment(name)}"
            counter += 1
        target.write_bytes(data)
        collected.append(target.name)

    try:
        if tarfile.is_tarfile(source):
            with tarfile.open(source, "r:*") as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    base = Path(member.name).name
                    if not LICENSE_BASENAME.match(base) or member.size > MAX_LICENSE_BYTES:
                        continue
                    fh = tf.extractfile(member)
                    if fh is not None:
                        store(member.name, fh.read(MAX_LICENSE_BYTES + 1))
            return collected
    except (tarfile.TarError, OSError):
        pass

    try:
        if zipfile.is_zipfile(source):
            with zipfile.ZipFile(source) as zf:
                for info in zf.infolist():
                    base = Path(info.filename).name
                    if info.is_dir() or not LICENSE_BASENAME.match(base) or info.file_size > MAX_LICENSE_BYTES:
                        continue
                    store(info.filename, zf.read(info))
    except (zipfile.BadZipFile, OSError):
        pass
    return collected



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


def parse_installed(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    cur: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw:
            if cur:
                records.append(cur)
                cur = {}
            continue
        if len(raw) >= 2 and raw[1] == ":":
            key, value = raw[0], raw[2:]
            cur[key] = value
    if cur:
        records.append(cur)
    return records


def copy_from_image(image: str, source: str, target: Path) -> None:
    cid = run(["docker", "create", image])
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        run(["docker", "cp", f"{cid}:{source}", str(target)], capture=False)
    finally:
        subprocess.run(["docker", "rm", "-f", cid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def git_has_path(repo: Path, commit: str, path: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{commit}:{path}/APKBUILD"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def export_tree(repo: Path, commit: str, source_path: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    p1 = subprocess.Popen(
        ["git", "-C", str(repo), "archive", "--format=tar", commit, source_path],
        stdout=subprocess.PIPE,
    )
    assert p1.stdout is not None
    p2 = subprocess.Popen(
        ["tar", "-x", "-C", str(destination), "--strip-components=2"],
        stdin=p1.stdout,
    )
    p1.stdout.close()
    rc2 = p2.wait()
    rc1 = p1.wait()
    if rc1 or rc2:
        raise RuntimeError(f"Failed to export {source_path} from aports commit {commit}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()

    output = Path(args.output).resolve()
    workspace = Path(args.workspace).resolve()
    output.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    bundle = workspace / "alpine-compliance"
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "metadata").mkdir(parents=True)
    (bundle / "aports").mkdir()
    (bundle / "distfiles").mkdir()

    raw_db = bundle / "metadata" / "installed"
    copy_from_image(args.image, "/lib/apk/db/installed", raw_db)
    copy_from_image(args.image, "/etc/alpine-release", bundle / "metadata" / "alpine-release")
    copy_from_image(args.image, "/etc/apk/arch", bundle / "metadata" / "arch")
    try:
        copy_from_image(args.image, "/etc/apk/repositories", bundle / "metadata" / "repositories")
    except subprocess.CalledProcessError:
        (bundle / "metadata" / "repositories").write_text("not present in final image\n", encoding="utf-8")

    alpine_release = (bundle / "metadata" / "alpine-release").read_text().strip()
    branch = ".".join(alpine_release.split(".")[:2])
    arch = (bundle / "metadata" / "arch").read_text().strip()
    if not branch or not arch:
        raise SystemExit("Could not determine Alpine release/architecture from final image")

    records = parse_installed(raw_db)
    if not records:
        raise SystemExit("Final image contains no readable APK installed database")

    manifest = bundle / "INSTALLED_APK_PACKAGES.tsv"
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["package", "version", "arch", "license", "origin", "aports_commit"])
        for rec in sorted(records, key=lambda r: (r.get("P", ""), r.get("V", ""))):
            missing = [key for key in ("P", "V", "A", "L", "o", "c") if not rec.get(key)]
            if missing:
                raise SystemExit(
                    f"APK package {rec.get('P', '<unknown>')} lacks required provenance fields: {', '.join(missing)}"
                )
            writer.writerow([rec["P"], rec["V"], rec["A"], rec["L"], rec["o"], rec["c"]])

    source_units: "OrderedDict[tuple[str, str], dict[str, object]]" = OrderedDict()
    for rec in records:
        key = (rec["o"], rec["c"])
        unit = source_units.setdefault(
            key,
            {"origin": rec["o"], "commit": rec["c"], "packages": [], "licenses": set()},
        )
        unit["packages"].append(f"{rec['P']}={rec['V']}")  # type: ignore[index]
        unit["licenses"].add(rec["L"])  # type: ignore[index]

    git_repo = workspace / "aports-git"
    if not (git_repo / ".git").exists():
        git_repo.mkdir(parents=True, exist_ok=True)
        run(["git", "init", str(git_repo)], capture=False)
        run(["git", "-C", str(git_repo), "remote", "add", "origin", APORTS_REMOTE], capture=False)

    fetched: set[str] = set()
    fetch_plan: list[tuple[str, str]] = []
    source_manifest = bundle / "ALPINE_SOURCE_UNITS.tsv"
    with source_manifest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["origin", "aports_commit", "repository", "installed_packages", "licenses", "source_path"])

        for (origin, commit), unit in sorted(source_units.items()):
            if commit not in fetched:
                run(
                    ["git", "-C", str(git_repo), "fetch", "--no-tags", "--depth=1", "origin", commit],
                    capture=False,
                )
                fetched.add(commit)

            repository = next((repo for repo in REPOSITORIES if git_has_path(git_repo, commit, f"{repo}/{origin}")), None)
            if repository is None:
                raise SystemExit(f"Could not locate APKBUILD for source package {origin} at aports commit {commit}")

            dest = bundle / "aports" / repository / origin
            export_tree(git_repo, commit, f"{repository}/{origin}", dest)
            rel = dest.relative_to(bundle).as_posix()
            unit_id = f"{repository}__{origin}__{commit[:12]}"
            fetch_plan.append((unit_id, rel))
            writer.writerow(
                [
                    origin,
                    commit,
                    repository,
                    ",".join(sorted(unit["packages"])),  # type: ignore[arg-type]
                    ",".join(sorted(unit["licenses"])),  # type: ignore[arg-type]
                    rel,
                ]
            )

    plan = bundle / "FETCH_PLAN.tsv"
    with plan.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        for unit_id, rel in fetch_plan:
            writer.writerow([unit_id, rel])

    helper = f"alpine:{branch}"
    run(["docker", "pull", helper], capture=False)
    helper_script = r'''
set -eu
apk add --no-cache abuild ca-certificates curl git wget >/dev/null
adduser -D -h /home/builder builder 2>/dev/null || true
addgroup builder abuild 2>/dev/null || true
while IFS="$(printf '\t')" read -r unit rel; do
  [ -n "$unit" ] || continue
  rm -rf /work
  mkdir -p /work "/compliance/distfiles/$unit"
  cp -a "/compliance/$rel/." /work/
  chown -R builder:abuild /work "/compliance/distfiles/$unit"
  su builder -c "cd /work && export SRCDEST='/compliance/distfiles/$unit' && abuild fetch"
done < /compliance/FETCH_PLAN.tsv
chmod -R a+rX /compliance/distfiles
'''
    run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{bundle}:/compliance",
            "--entrypoint",
            "/bin/sh",
            helper,
            "-c",
            helper_script,
        ],
        capture=False,
    )

    license_dir = bundle / "license-material"
    license_rows: list[list[str]] = []
    for unit_id, rel in fetch_plan:
        local_source_dir = bundle / rel
        for candidate in sorted(local_source_dir.rglob("*")):
            if candidate.is_file() and LICENSE_BASENAME.match(candidate.name) and candidate.stat().st_size <= MAX_LICENSE_BYTES:
                target = license_dir / f"{_safe_fragment(unit_id)}__aports__{_safe_fragment(candidate.relative_to(local_source_dir).as_posix())}"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, target)
                license_rows.append([unit_id, candidate.relative_to(bundle).as_posix(), target.relative_to(bundle).as_posix()])
        dist_dir = bundle / "distfiles" / unit_id
        if dist_dir.is_dir():
            for source in sorted(dist_dir.iterdir()):
                if not source.is_file():
                    continue
                for name in collect_license_material(source, license_dir, f"{unit_id}__{source.name}"):
                    license_rows.append([unit_id, source.relative_to(bundle).as_posix(), f"license-material/{name}"])

    with (bundle / "LICENSE_MATERIAL.tsv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["source_unit", "source", "extracted_license_or_notice"])
        writer.writerows(license_rows)

    checksums = bundle / "SOURCE_SHA256SUMS"
    with checksums.open("w", encoding="utf-8") as fh:
        for path in sorted(bundle.rglob("*")):
            if path.is_file() and path != checksums:
                fh.write(f"{sha256(path)}  {path.relative_to(bundle).as_posix()}\n")

    archive = output / f"alpine-corresponding-source-{alpine_release}-{arch}.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(bundle, arcname=f"alpine-corresponding-source-{alpine_release}-{arch}")

    shutil.copy2(manifest, output / "ALPINE_PACKAGES.tsv")
    shutil.copy2(source_manifest, output / "ALPINE_SOURCE_UNITS.tsv")

    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
