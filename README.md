# docker-ddclient

[![Build ddclient](https://github.com/fwe86/docker-ddclient/actions/workflows/build.yml/badge.svg)](https://github.com/fwe86/docker-ddclient/actions/workflows/build.yml)
[![GitHub Container Registry](https://img.shields.io/badge/GHCR-docker--ddclient-blue?logo=github)](https://github.com/fwe86/docker-ddclient/pkgs/container/docker-ddclient)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Automated Docker builds of [ddclient](https://github.com/ddclient/ddclient) based on the official [LinuxServer.io ddclient Docker repository](https://github.com/linuxserver/docker-ddclient).

The purpose of this repository is to provide an up-to-date LinuxServer.io-based ddclient image that automatically tracks the **newest published ddclient release, including pre-releases**.

> **Independent project:** This repository and the images published from it are not affiliated with, endorsed by, or maintained by LinuxServer.io or the ddclient project.

## Quick start

Pull the latest successfully built image:

```bash
docker pull ghcr.io/fwe86/docker-ddclient:latest
```

For reproducible deployments, use the fully qualified ddclient/LinuxServer.io version tag instead of `latest`, for example:

```bash
docker pull ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1-ls233
```

Available images are published to the [GitHub Container Registry](https://github.com/fwe86/docker-ddclient/pkgs/container/docker-ddclient).

## Why does this repository exist?

The official LinuxServer.io ddclient build determines the latest stable ddclient release through GitHub's `releases/latest` API when no explicit version is supplied during the build.

GitHub's `releases/latest` endpoint does not select pre-releases such as release candidates. This can result in a newer published ddclient pre-release being available while the official LinuxServer.io image still uses the previous stable version.

This repository deliberately selects the newest published ddclient release, including pre-releases, and supplies it to LinuxServer.io's existing `DDCLIENT_VERSION` build mechanism.

The LinuxServer.io source release is built unchanged as an intermediate image. A small project-owned final-stage Dockerfile then applies this project's own image identity, provenance metadata, and init branding. No LinuxServer.io Dockerfile or root filesystem file is copied into or maintained by this repository.

## How it works

The GitHub Actions workflow periodically checks two upstream projects:

- [ddclient/ddclient](https://github.com/ddclient/ddclient)
- [linuxserver/docker-ddclient](https://github.com/linuxserver/docker-ddclient)

For ddclient, the newest **published release** is selected. This deliberately includes published pre-releases such as release candidates, but excludes drafts and unpublished development versions.

For LinuxServer.io, the latest published `docker-ddclient` release is used.

For each build:

1. the exact LinuxServer.io release tag is checked out and verified;
2. the selected ddclient release is supplied through LinuxServer.io's existing `DDCLIENT_VERSION` build argument;
3. that unchanged LinuxServer.io source tree is built as an intermediate image;
4. the project-owned final-stage `Dockerfile` creates the published image;
5. LinuxServer.io branding inherited from the upstream image is replaced with project-specific branding;
6. image identity, provenance, and the ddclient version are verified before publication;
7. an SPDX JSON SBOM is generated from the final image;
8. source archives, license files, wrapper source, branding, SBOM, and checksums are published with a matching GitHub Release.

In simplified form:

```text
ddclient latest published release
              │
              ├──────────────┐
              │              │
              ▼              ▼
        v4.0.1-rc.1     LinuxServer.io
                         v4.0.0-ls233
                              │
              ┌───────────────┘
              ▼
       v4.0.1-rc.1-ls233
              │
              ▼
   Does this image already exist?
          │           │
         yes          no
          │           │
        stop          ▼
            Verify LSIO source
                      │
                      ▼
          Build unchanged LSIO image
                      │
                      ▼
           Build independent wrapper
                      │
                      ▼
       Verify identity and branding
                      │
                      ▼
              Verify ddclient
                      │
                      ▼
             Generate SPDX SBOM
                      │
                      ▼
            Generate SHA256SUMS
                      │
                      ▼
                Publish GHCR
                      │
                      ▼
        Publish source/compliance release
                      │
                      ▼
               Update .upstream
```

## Independent image identity and branding

The image published by this repository is **not** an official LinuxServer.io image.

LinuxServer.io documents that images based on or forked from its images should use their own branding and that non-first-party images must set `LSIO_FIRST_PARTY=false` when replacing the init branding.

The project-owned final stage therefore:

- sets `LSIO_FIRST_PARTY=false`;
- provides its own `/etc/s6-overlay/s6-rc.d/init-adduser/branding`;
- replaces the inherited `/build_version`;
- identifies `fwe86` as maintainer, author, and vendor of the published image;
- replaces inherited title, source, documentation, version, and revision metadata relevant to image identity;
- preserves the exact LinuxServer.io release and source commit in dedicated provenance labels.

LinuxServer.io remains explicitly credited as the upstream container source. The branding changes only distinguish responsibility for the independently published image.

Relevant image labels include:

```text
maintainer=fwe86
org.opencontainers.image.authors=fwe86
org.opencontainers.image.vendor=fwe86
org.opencontainers.image.title=docker-ddclient
org.opencontainers.image.source=https://github.com/fwe86/docker-ddclient
io.github.fwe86.ddclient.version=<ddclient release>
io.github.fwe86.linuxserver.release=<LinuxServer.io release>
io.github.fwe86.linuxserver.revision=<LinuxServer.io commit>
```

The workflow checks these values and fails before publication if the independent branding is not present or the old `Linuxserver.io version` identification remains in `build_version` or `/build_version`.

## Automatic builds

The workflow periodically determines:

1. the latest published LinuxServer.io `docker-ddclient` release;
2. the latest published ddclient release, including pre-releases;
3. the resulting unique ddclient/LinuxServer.io version combination;
4. whether an image for this exact combination already exists.

If the image already exists, no build is performed.

If either upstream project publishes a relevant new release, a new version combination is detected and automatically built.

The workflow can also be started manually using **Actions → Build ddclient → Run workflow**. A manual run can optionally force a rebuild of an already existing version.

## Image tags

Images are published to:

```text
ghcr.io/fwe86/docker-ddclient
```

Each successful build publishes four tags.

For example, with ddclient `v4.0.1-rc.1` and LinuxServer.io build `ls233`:

```text
ghcr.io/fwe86/docker-ddclient:latest
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1
ghcr.io/fwe86/docker-ddclient:ls233
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1-ls233
```

### `latest`

```text
ghcr.io/fwe86/docker-ddclient:latest
```

Points to the newest successfully built combination.

### ddclient version

```text
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1
```

Points to the newest LinuxServer.io build produced with this specific ddclient version.

### LinuxServer.io build

```text
ghcr.io/fwe86/docker-ddclient:ls233
```

Points to the newest ddclient release built from this specific LinuxServer.io release.

### Exact version

```text
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1-ls233
```

Identifies the exact combination of the ddclient release and LinuxServer.io build.

Use this tag when reproducibility and explicit version pinning are important.

## Source availability and compliance material

For every newly published image combination, the workflow creates a corresponding GitHub Release.

For an image such as:

```text
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1-ls233
```

the corresponding release is:

```text
image-v4.0.1-rc.1-ls233
```

The release contains:

```text
linuxserver-docker-ddclient-v4.0.0-ls233.tar.gz
ddclient-v4.0.1-rc.1.tar.gz
LICENSE-linuxserver-docker-ddclient
LICENSE-ddclient
COPYRIGHT-ddclient
Dockerfile-final
branding
SOURCE_INFO.txt
SBOM.spdx.json
SHA256SUMS
```

### LinuxServer.io source

The LinuxServer.io archive is created from the exact Git tag verified and used to build the intermediate image. Its original license file is published separately unchanged.

### ddclient source

The ddclient archive contains the exact published ddclient release selected through `DDCLIENT_VERSION`. Its license and copyright files are published separately unchanged.

### Project-owned final stage

`Dockerfile-final` and `branding` are the exact project-owned files used to create the final independently branded image. Publishing these files alongside the upstream source archives records the complete project-owned transformation applied after the unchanged LinuxServer.io build.

### SBOM

`SBOM.spdx.json` is generated from the final built container image in SPDX JSON format. It provides an inventory of components detected in the final image, including packages inherited from the LinuxServer.io base image and packages installed by the upstream build.

An SBOM is an inventory and does not replace any source-disclosure or license obligations. Upstream components remain subject to their respective licenses.

### Checksums

`SHA256SUMS` contains SHA-256 checksums for:

- both upstream source archives;
- both separately published license files;
- ddclient copyright information;
- `Dockerfile-final`;
- `branding`;
- `SOURCE_INFO.txt`;
- `SBOM.spdx.json`.

The workflow creates the checksum file only after the SBOM has been generated.

## Upstream state

After a new image has been successfully built, verified, published, and its source/compliance release has been created, the workflow updates the `.upstream` file in this repository.

Example:

```text
DDCLIENT_VERSION=v4.0.1-rc.1
LSIO_RELEASE=v4.0.0-ls233
LSIO_BUILD=ls233
IMAGE=ghcr.io/fwe86/docker-ddclient
IMAGE_VERSION=v4.0.1-rc.1-ls233
SOURCE_RELEASE=image-v4.0.1-rc.1-ls233
```

The file represents the **last successfully built and published upstream combination**.

It is updated only after:

1. the Docker image has been built successfully;
2. the independent image identity and branding have been verified;
3. the resulting ddclient version has been verified;
4. the SPDX SBOM and release checksums have been generated;
5. all image tags have been successfully published to GHCR;
6. the corresponding source/compliance release has been published.

The Git history therefore also provides a history of successfully processed upstream releases.

## Verification

### LinuxServer.io release verification

The workflow checks out the exact LinuxServer.io release tag detected through the GitHub API and verifies that the checked-out commit matches the commit referenced by that release tag.

A mismatch causes the workflow to fail before the image is built.

### Project revision verification

The project repository is checked out at the exact workflow commit. The workflow records that commit and fails if the checked-out revision does not match `GITHUB_SHA`.

### Image identity and branding verification

Before publication, the workflow verifies:

- `maintainer=fwe86`;
- project author, vendor, title, source, version, and revision labels;
- exact ddclient and LinuxServer.io provenance labels;
- `LSIO_FIRST_PARTY=false`;
- project-specific `build_version`;
- project-specific `/build_version`;
- project-specific init branding;
- absence of the old `Linuxserver.io version` identity from `build_version` and `/build_version`.

A mismatch prevents publication.

### ddclient version verification

After building the final image, ddclient is executed inside the resulting container:

```bash
ddclient --version
```

The reported version must match the ddclient release selected by the workflow.

A mismatch prevents the image from being published.

### SBOM verification

The workflow generates `SBOM.spdx.json` from the final image and checks that the file exists, is non-empty, and contains the expected SPDX JSON structure before continuing.

### Publication order

The workflow follows this sequence:

```text
Detect upstream versions
        ↓
Verify LinuxServer.io source
        ↓
Archive upstream sources and licenses
        ↓
Build unchanged LinuxServer.io image
        ↓
Build independent final image
        ↓
Verify image identity and branding
        ↓
Verify ddclient version
        ↓
Generate and verify SPDX SBOM
        ↓
Generate SHA256SUMS
        ↓
Publish all GHCR tags
        ↓
Publish source/compliance release
        ↓
Update .upstream
```

A failed source check, build, identity check, version check, SBOM generation, registry push, or release publication therefore does not update `.upstream`.

## Usage

The image retains the LinuxServer.io container structure and configuration.

Example Docker Compose configuration:

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

For configuration options, environment variables, volumes, permissions, and general container usage, refer to the official [LinuxServer.io ddclient documentation](https://docs.linuxserver.io/images/docker-ddclient/). Keep in mind that this repository publishes an independent derivative image, not an official LinuxServer.io image.

## Update policy

This project deliberately follows the newest **published** ddclient release, including pre-releases.

This means that `latest` may point to an image containing a release candidate or another upstream pre-release.

If you require a fixed or previously tested version, do not rely on `latest`. Pin the image to an explicit tag instead:

```text
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1-ls233
```

The workflow never builds arbitrary commits from ddclient's development branch. Only releases that have actually been published by the ddclient project are considered.

## Architectures

Images produced by this repository currently follow the architecture used by the GitHub-hosted build runner.

They should not be assumed to provide the same multi-architecture manifest as the official LinuxServer.io image.

The official LinuxServer.io ddclient image may support additional architectures that this repository does not currently reproduce.

## Relationship to the upstream projects

This repository does **not** maintain a fork of ddclient or a copied fork of LinuxServer.io's Docker implementation.

The resulting image is assembled from:

- the original LinuxServer.io `docker-ddclient` source at a published LinuxServer.io release;
- an official published ddclient release selected through LinuxServer.io's existing `DDCLIENT_VERSION` mechanism;
- a small project-owned final image layer used solely for independent branding, provenance metadata, and image identification.

Upstream projects:

- [ddclient/ddclient](https://github.com/ddclient/ddclient)
- [linuxserver/docker-ddclient](https://github.com/linuxserver/docker-ddclient)

Issues specific to ddclient itself or the LinuxServer.io container should be reported to the corresponding upstream project.

Issues specific to the automation, final-stage wrapper, or images published by this repository should be reported here.

## License

Original content in this repository is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE).

Upstream software retains its original copyright and licensing:

- **LinuxServer.io docker-ddclient** — GNU General Public License v3.0
- **ddclient** — GNU General Public License v2.0 or later

The resulting Docker image also contains third-party software under additional licenses. The presence of this repository's GPL-3.0 license does not relicense those components.

The SPDX SBOM is provided to improve transparency about components detected in the final image. It does not alter the license of any component and does not by itself replace source-code or notice obligations.

Copyright and license terms of all upstream components remain with their respective copyright holders.

## Disclaimer

This is an independent project and is **not affiliated with, endorsed by, or maintained by LinuxServer.io or the ddclient project**.

Pre-release versions of ddclient may contain bugs, regressions, or incomplete functionality.

If stability is more important than access to the newest published ddclient release, consider using the official LinuxServer.io image or pin this image to a version that you have tested.
