#!/usr/bin/env python3
"""Collect exact source archives for CPAN distributions installed in the image.

Installed .packlist files under /usr/local are used as the authoritative list.
Each top-level module is resolved at its installed version through MetaCPAN.  If
an installed module cannot be mapped to an exact release tarball, the script
fails before the container image may be published.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

META_BASE = "https://fastapi.metacpan.org/v1/download_url/"

LICENSE_BASENAME = re.compile(r"^(?:license|licence|copying|copyright|notice)(?:[._-].*)?$", re.IGNORECASE)
MAX_LICENSE_BYTES = 2 * 1024 * 1024


def collect_license_material(source: Path, destination: Path, prefix: str) -> list[str]:
    collected: list[str] = []
    destination.mkdir(parents=True, exist_ok=True)

    def store(name: str, data: bytes) -> None:
        if len(data) > MAX_LICENSE_BYTES:
            return
        target = destination / f"{safe_name(prefix)}__{safe_name(name)}"
        counter = 1
        while target.exists():
            target = destination / f"{safe_name(prefix)}__{counter}__{safe_name(name)}"
            counter += 1
        target.write_bytes(data)
        collected.append(target.name)

    try:
        if tarfile.is_tarfile(source):
            with tarfile.open(source, "r:*") as tf:
                for member in tf.getmembers():
                    if not member.isfile() or member.size > MAX_LICENSE_BYTES:
                        continue
                    if not LICENSE_BASENAME.match(Path(member.name).name):
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
                    if info.is_dir() or info.file_size > MAX_LICENSE_BYTES:
                        continue
                    if not LICENSE_BASENAME.match(Path(info.filename).name):
                        continue
                    store(info.filename, zf.read(info))
    except (zipfile.BadZipFile, OSError):
        pass
    return collected



def run(args: list[str]) -> str:
    proc = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stdout.strip()


def docker_run(image: str, command: list[str]) -> str:
    return run(["docker", "run", "--rm", "--entrypoint", command[0], image, *command[1:]])


def module_from_packlist(path: str) -> str:
    marker = "/auto/"
    if marker not in path or not path.endswith("/.packlist"):
        raise ValueError(f"Unsupported .packlist path: {path}")
    rel = path.split(marker, 1)[1][: -len("/.packlist")]
    parts = [p for p in rel.split("/") if p]
    if not parts:
        raise ValueError(f"Could not derive module name from {path}")
    return "::".join(parts)


def installed_version(image: str, module: str) -> str:
    code = r'''
use strict;
use warnings;
use Module::Metadata;
my $m = Module::Metadata->new_from_module($ARGV[0]);
die "module metadata not found\n" unless $m;
my $v = $m->version;
die "module version not found\n" unless defined $v;
print "$v";
'''
    return docker_run(image, ["perl", "-MModule::Metadata", "-e", code, module]).strip()


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "fwe86/docker-ddclient compliance collector"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def download(url: str, target: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "fwe86/docker-ddclient compliance collector"})
    with urllib.request.urlopen(req, timeout=120) as response, target.open("wb") as fh:
        shutil.copyfileobj(response, fh)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", value)


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

    bundle = workspace / "cpan-compliance"
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "metacpan").mkdir(parents=True)
    (bundle / "sources").mkdir()

    listing = docker_run(
        args.image,
        ["/bin/sh", "-c", "find /usr/local -type f -name .packlist -print 2>/dev/null | sort"],
    )
    packlists = [line.strip() for line in listing.splitlines() if line.strip()]
    (bundle / "PACKLISTS.txt").write_text("\n".join(packlists) + ("\n" if packlists else ""), encoding="utf-8")

    modules: dict[str, dict[str, str]] = {}
    for packlist in packlists:
        module = module_from_packlist(packlist)
        version = installed_version(args.image, module)
        if not version:
            raise SystemExit(f"Could not determine installed version for CPAN module {module}")
        modules[module] = {"version": version, "packlist": packlist}

    manifest_rows: list[list[str]] = []
    downloaded: dict[str, tuple[str, str]] = {}
    for module in sorted(modules):
        version = modules[module]["version"]
        query = urllib.parse.urlencode({"version": "==" + version})
        api_url = META_BASE + urllib.parse.quote(module, safe="") + "?" + query
        metadata = fetch_json(api_url)
        download_url = metadata.get("download_url")
        if not download_url:
            raise SystemExit(f"MetaCPAN did not provide an exact source URL for {module} {version}")

        meta_file = bundle / "metacpan" / f"{safe_name(module)}-{safe_name(version)}.json"
        meta_file.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        if download_url in downloaded:
            source_file, digest = downloaded[download_url]
        else:
            basename = Path(urllib.parse.urlparse(download_url).path).name
            if not basename:
                raise SystemExit(f"Invalid MetaCPAN download URL for {module}: {download_url}")
            target = bundle / "sources" / basename
            if target.exists():
                target = bundle / "sources" / f"{safe_name(module)}-{basename}"
            download(download_url, target)
            digest = sha256(target)
            source_file = target.relative_to(bundle).as_posix()
            downloaded[download_url] = (source_file, digest)

        manifest_rows.append(
            [
                module,
                version,
                metadata.get("distribution", ""),
                metadata.get("author", ""),
                metadata.get("release", ""),
                download_url,
                source_file,
                digest,
                modules[module]["packlist"],
            ]
        )

    license_dir = bundle / "license-material"
    license_rows: list[list[str]] = []
    for source in sorted((bundle / "sources").iterdir()):
        if source.is_file():
            for name in collect_license_material(source, license_dir, source.name):
                license_rows.append([source.name, f"license-material/{name}"])
    with (bundle / "LICENSE_MATERIAL.tsv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["source_archive", "extracted_license_or_notice"])
        writer.writerows(license_rows)

    manifest = bundle / "CPAN_COMPONENTS.tsv"
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(
            [
                "module",
                "installed_version",
                "distribution",
                "author",
                "release",
                "source_url",
                "source_file",
                "sha256",
                "packlist",
            ]
        )
        writer.writerows(manifest_rows)

    checksums = bundle / "SOURCE_SHA256SUMS"
    with checksums.open("w", encoding="utf-8") as fh:
        for path in sorted(bundle.rglob("*")):
            if path.is_file() and path != checksums:
                fh.write(f"{sha256(path)}  {path.relative_to(bundle).as_posix()}\n")

    archive = output / "cpan-corresponding-source.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(bundle, arcname="cpan-corresponding-source")

    shutil.copy2(manifest, output / "CPAN_COMPONENTS.tsv")

    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
