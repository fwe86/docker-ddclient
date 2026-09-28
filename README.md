# docker-ddclient

[![Build ddclient](https://github.com/fwe86/docker-ddclient/actions/workflows/build.yml/badge.svg)](https://github.com/fwe86/docker-ddclient/actions/workflows/build.yml)
[![GitHub Container Registry](https://img.shields.io/badge/GHCR-docker--ddclient-blue?logo=github)](https://github.com/fwe86/docker-ddclient/pkgs/container/docker-ddclient)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Automated Docker builds of [ddclient](https://github.com/ddclient/ddclient)
based on the official
[LinuxServer.io ddclient Docker repository](https://github.com/linuxserver/docker-ddclient).

The purpose of this repository is to provide an up-to-date LinuxServer.io-based
ddclient image that automatically tracks the **newest published ddclient
release, including pre-releases**.

> **Independent project:** This repository and the images published from it are
> not affiliated with, endorsed by, or maintained by LinuxServer.io or the
> ddclient project.

## Quick start

```bash
docker pull ghcr.io/fwe86/docker-ddclient:latest
```

For reproducible deployments, use the exact ddclient/LinuxServer.io combination
instead of `latest`, for example:

```bash
docker pull ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1-ls233
```

Exact combination tags are immutable once published.

## Why this repository exists

The official LinuxServer.io ddclient build can be supplied an explicit
`DDCLIENT_VERSION`. This project determines the newest **published** ddclient
release itself, including release candidates and other published pre-releases,
and supplies that release to LinuxServer.io's existing build mechanism.

The project does not maintain a copied fork of the LinuxServer.io container
implementation. It checks out an exact published LinuxServer.io release and
adds only a small project-owned final stage for independent image identity,
provenance, and init branding.

## Build and publication process

The workflow checks:

- `ddclient/ddclient` for the newest published release, including pre-releases;
- `linuxserver/docker-ddclient` for the latest published LinuxServer.io release.

For a new version combination it then:

1. verifies the exact LinuxServer.io source tag and commit;
2. archives the exact project, LinuxServer.io, and ddclient sources;
3. resolves the moving LinuxServer.io base-image tag to an immutable registry
   digest;
4. archives the corresponding LinuxServer.io base and s6-overlay source;
5. builds the LinuxServer.io source using a mechanically generated Dockerfile
   whose only intended source change is the base-image `FROM` pin;
6. builds the independently branded project final stage;
7. verifies image identity, upstream provenance, branding, and ddclient version;
8. inventories every APK package actually present in the final image and
   collects the exact Alpine aports recipe plus fetched/verified source inputs;
9. discovers CPAN distributions actually installed below `/usr/local` and
   collects their exact source releases;
10. generates and verifies an SPDX JSON SBOM;
11. creates SHA-256 checksums and an immutable GitHub compliance release;
12. verifies that source/compliance release **before** logging into GHCR;
13. publishes mutable convenience tags and finally the immutable exact tag;
14. attaches the registry digest to the already published compliance release;
15. updates `.upstream` only after successful publication.

The detailed compliance design is documented in [COMPLIANCE.md](COMPLIANCE.md).

## Source-before-binary publication

The compliance release is intentionally published before the GHCR image.
Therefore a failed source collection, checksum validation, SBOM generation, or
GitHub source release stops the workflow before this project distributes the
new container image.

Every final image includes labels identifying its exact compliance release,
LinuxServer.io release/commit, LinuxServer.io base-image digest/source release,
and project revision.

## Immutable exact tags

For an upstream combination such as ddclient `v4.0.1-rc.1` and LinuxServer.io
build `ls233`, the exact tag is:

```text
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1-ls233
```

If that exact tag already exists, the workflow stops. There is deliberately no
force-rebuild option and no code path that overwrites an exact image tag.

A rebuild that is genuinely required must therefore use a new image version or
an explicitly changed versioning scheme rather than silently replacing already
distributed object code.

## Image tags

Each successful build publishes four tags:

```text
ghcr.io/fwe86/docker-ddclient:latest
ghcr.io/fwe86/docker-ddclient:<ddclient-release>
ghcr.io/fwe86/docker-ddclient:ls<LinuxServer-build>
ghcr.io/fwe86/docker-ddclient:<ddclient-release>-ls<LinuxServer-build>
```

The first three are convenience aliases and may move. The final combined tag is
immutable and should be used when explicit version pinning is important.

## Independent image identity and branding

The image published by this repository is **not** an official LinuxServer.io
image.

The project-owned final stage:

- sets `LSIO_FIRST_PARTY=false`;
- provides its own `/etc/s6-overlay/s6-rc.d/init-adduser/branding`;
- replaces the inherited `/build_version` identity;
- identifies `fwe86` as maintainer, author, and vendor of the published image;
- uses project-owned source/documentation/revision labels;
- records LinuxServer.io and ddclient information separately as upstream
  provenance;
- records the exact LinuxServer.io base-image digest and compliance release.

Relevant labels include:

```text
maintainer=fwe86
org.opencontainers.image.authors=fwe86
org.opencontainers.image.vendor=fwe86
org.opencontainers.image.title=docker-ddclient
org.opencontainers.image.source=https://github.com/fwe86/docker-ddclient
io.github.fwe86.ddclient.version=<ddclient release>
io.github.fwe86.linuxserver.release=<LinuxServer.io release>
io.github.fwe86.linuxserver.revision=<LinuxServer.io commit>
io.github.fwe86.linuxserver.base.digest=<base image digest>
io.github.fwe86.compliance.release=<GitHub compliance release>
io.github.fwe86.compliance.url=<GitHub compliance release URL>
```

The project intentionally does **not** assign one blanket OCI license expression
to the complete image. The image contains components under multiple licenses;
component-level license information is represented by the source material and
SBOM.

## Compliance release contents

Compliance release names are unique per successful build attempt:

```text
image-<exact-image-tag>-run-<GitHub-run-id>-<attempt>
```

They are never overwritten. Depending on the upstream package set, assets
include:

```text
fwe86-docker-ddclient-<commit>.tar.gz
linuxserver-docker-ddclient-<release>.tar.gz
linuxserver-docker-baseimage-alpine-<release>.tar.gz
ddclient-<release>.tar.gz
s6-overlay-<release>.tar.gz
linuxserver-base-embedded-scripts.tar.gz
alpine-corresponding-source-<release>-<arch>.tar.gz
cpan-corresponding-source.tar.gz
ALPINE_PACKAGES.tsv
ALPINE_SOURCE_UNITS.tsv
CPAN_COMPONENTS.tsv
LICENSE-*
COPYRIGHT-ddclient
Dockerfile-linuxserver-original
Dockerfile-linuxserver-pinned
Dockerfile-linuxserver-base-pin.diff
Dockerfile-final
LINUXSERVER_BASE_IMAGE.json
BASE_SOURCE_INFO.txt
SOURCE_INFO.txt
BUILD_INPUTS.json
SBOM.spdx.json
SHA256SUMS
RELEASE_NOTES.md
```

After the exact image has been published, `IMAGE_DIGESTS.txt` is added to the
same release with the immutable GHCR digest.

### Alpine corresponding source

The workflow reads the APK installed database from the final image. For every
installed package it records the exact source-package origin and aports commit,
archives the matching `APKBUILD` directory and local patches/scripts, and uses
Alpine `abuild fetch` to retrieve and verify the referenced remote source
inputs.

This is done for **all** installed Alpine packages rather than only packages
pre-classified as GPL/copyleft.

### CPAN corresponding source

Installed CPAN modules are discovered from `.packlist` files. Their installed
versions are determined inside the final image and resolved to exact MetaCPAN
release archives. Failure to map an installed module to exact source stops the
build.

### SBOM

`SBOM.spdx.json` is generated from the final built image. ddclient is explicitly
represented as `GPL-2.0-or-later` because it is installed outside Alpine package
metadata. The built ddclient version is independently verified with
`ddclient --version`.

An SBOM is an inventory and does not replace source-code, copyright, attribution,
or notice obligations.

## Automatic builds

The workflow runs hourly and can also be started manually through:

**Actions → Build ddclient → Run workflow**

There is no force-rebuild switch. If the exact version tag already exists, no
new image is built or published.

## Upstream state

After successful source disclosure and image publication, `.upstream` records
the exact state, including:

```text
DDCLIENT_VERSION=...
DDCLIENT_COMMIT=...
LSIO_RELEASE=...
LSIO_VERSION=...
LSIO_BUILD=...
LSIO_COMMIT=...
LSIO_BASE_IMAGE=...
LSIO_BASE_DIGEST=...
LSIO_BASE_RELEASE=...
LSIO_BASE_COMMIT=...
IMAGE=...
IMAGE_DIGEST=...
COMPLIANCE_RELEASE=...
PROJECT_REVISION=...
```

This update happens only after the new source release and image have both been
successfully published.

## Usage

The image retains the LinuxServer.io container structure and configuration.

```yaml
services:
  ddclient:
    image: ghcr.io/fwe86/docker-ddclient:latest
    container_name: ddclient
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Berlin
    volumes:
      - ./config:/config
    restart: unless-stopped
```

For configuration options, volumes, permissions, and general container usage,
refer to the official
[LinuxServer.io ddclient documentation](https://docs.linuxserver.io/images/docker-ddclient/).
This project publishes an independent derivative image, not an official
LinuxServer.io image.

## Update policy

`latest` deliberately follows the newest **published** ddclient release,
including published pre-releases. It may therefore point to a release candidate.

For a fixed deployment, pin the exact combined version tag rather than
`latest`.

The workflow never builds arbitrary ddclient development commits; only
published ddclient releases are considered.

## Architectures

Images produced by this repository currently follow the architecture of the
GitHub-hosted build runner. They should not be assumed to reproduce the official
LinuxServer.io multi-architecture manifest.

## Relationship to upstream projects

Upstream projects:

- [ddclient/ddclient](https://github.com/ddclient/ddclient)
- [linuxserver/docker-ddclient](https://github.com/linuxserver/docker-ddclient)

Issues in ddclient itself or the LinuxServer.io container should be reported to
the respective upstream project. Issues in this project's automation, final
wrapper, compliance tooling, or published derivative images belong here.

## License

Original content in this repository is licensed under the **GNU General Public
License v3.0**. See [LICENSE](LICENSE).

Upstream software retains its own copyright and license terms. In particular:

- LinuxServer.io `docker-ddclient` — GNU GPL v3.0;
- ddclient — GNU GPL v2.0 or later;
- Alpine packages, s6-overlay components, Perl modules, and other included
  software — their respective upstream licenses.

The repository's GPL-3.0 license does not purport to relicense the complete
multi-license container image.

## Disclaimer

This is an independent project and is **not affiliated with, endorsed by, or
maintained by LinuxServer.io or the ddclient project**.

Pre-release ddclient versions may contain bugs, regressions, or incomplete
functionality. If stability is more important than following the newest
published ddclient release, use an explicitly tested version or the official
LinuxServer.io image.
