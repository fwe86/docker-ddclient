# docker-ddclient

[![Build ddclient](https://github.com/fwe86/docker-ddclient/actions/workflows/build.yml/badge.svg)](https://github.com/fwe86/docker-ddclient/actions/workflows/build.yml)
[![GitHub Container Registry](https://img.shields.io/badge/GHCR-docker--ddclient-blue?logo=github)](https://github.com/fwe86/docker-ddclient/pkgs/container/docker-ddclient)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Automated Docker builds of [ddclient](https://github.com/ddclient/ddclient) based on the official [LinuxServer.io ddclient Docker repository](https://github.com/linuxserver/docker-ddclient).

The purpose of this repository is to provide an up-to-date LinuxServer.io-based ddclient image that automatically tracks the **newest published ddclient release, including pre-releases**.

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

The official LinuxServer.io ddclient image determines the latest stable ddclient release through GitHub's `releases/latest` API when no explicit version is supplied during the build.

GitHub does not consider pre-releases such as release candidates (`rc`) to be the latest stable release.

This can result in a newer published ddclient release being available while the official LinuxServer.io image still uses the previous stable version.

This repository solves that problem without maintaining a custom Dockerfile or modifying the LinuxServer.io container structure.

## How it works

The GitHub Actions workflow periodically checks two upstream projects:

- [ddclient/ddclient](https://github.com/ddclient/ddclient)
- [linuxserver/docker-ddclient](https://github.com/linuxserver/docker-ddclient)

For ddclient, the newest **published release** is selected. This deliberately includes published pre-releases such as release candidates, but excludes drafts and unpublished development versions.

For LinuxServer.io, the latest published `docker-ddclient` release is used.

The resulting image is built directly from the corresponding LinuxServer.io release tag while supplying the detected ddclient version through LinuxServer.io's existing `DDCLIENT_VERSION` build argument.

In simplified form:

```text
ddclient latest published release
              │
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
                 Build image
                      │
                      ▼
              Verify ddclient
                      │
                      ▼
                 Publish GHCR
                      │
                      ▼
               Update .upstream
```

No LinuxServer.io Dockerfile, root filesystem files, or other build files are maintained as copies in this repository.

For each build, the workflow checks out the original LinuxServer.io repository at the detected release tag and builds that upstream source while explicitly selecting the desired ddclient release.

## Automatic builds

The workflow runs periodically and determines:

1. the latest published LinuxServer.io `docker-ddclient` release;
2. the latest published ddclient release, including pre-releases;
3. the resulting unique ddclient/LinuxServer.io version combination;
4. whether an image for this exact combination already exists.

If the image already exists, no build is performed.

If either upstream project publishes a relevant new release, a new version combination is detected and automatically built.

The workflow can also be started manually using **Actions → Build ddclient → Run workflow**.

A manual run can optionally force a rebuild of an already existing version.

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

Identifies the exact combination of ddclient release and LinuxServer.io build.

Use this tag when reproducibility and explicit version pinning are important.

## Upstream state

After a new image has been successfully built, verified, and published, the workflow updates the `.upstream` file in this repository.

Example:

```text
DDCLIENT_VERSION=v4.0.1-rc.1
LSIO_RELEASE=v4.0.0-ls233
LSIO_BUILD=ls233
IMAGE=ghcr.io/fwe86/docker-ddclient
IMAGE_VERSION=v4.0.1-rc.1-ls233
```

The file represents the **last successfully built and published upstream combination**.

It is updated only after:

1. the Docker image has been built successfully;
2. the resulting ddclient version has been verified;
3. all image tags have been successfully published to GHCR.

The Git history therefore also provides a simple history of successfully processed upstream releases.

## Verification

The workflow performs several checks before recording a build as successful.

### LinuxServer.io release verification

The workflow checks out the exact LinuxServer.io release tag that was detected through the GitHub API.

It then verifies that the checked-out commit matches the commit referenced by that release tag.

A mismatch causes the workflow to fail before the image is built.

### ddclient version verification

After building the image, ddclient is executed inside the resulting container:

```bash
ddclient --version
```

The reported version must match the ddclient release selected by the workflow.

A mismatch prevents the image from being published.

### Publication order

The upstream state is updated only after the complete build and publication sequence succeeds:

```text
Detect upstream versions
        ↓
Verify LinuxServer.io source
        ↓
Build image
        ↓
Verify ddclient version
        ↓
Publish all GHCR tags
        ↓
Update .upstream
```

A failed build, failed version check, or failed registry push therefore does not update `.upstream`.

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

For configuration options, environment variables, volumes, permissions, and general container usage, refer to the official [LinuxServer.io ddclient documentation](https://docs.linuxserver.io/images/docker-ddclient/).

## Update policy

This project deliberately follows the newest **published** ddclient release, including pre-releases.

This means that `latest` may point to an image containing a release candidate or another upstream pre-release.

If you require a fixed or previously tested version, do not rely on `latest`. Pin the image to an explicit tag instead:

```text
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1-ls233
```

The workflow never builds arbitrary commits from ddclient's development branch. Only releases that have actually been published by the ddclient project are considered.

## Relationship to the upstream projects

This repository does **not** maintain a fork of ddclient or LinuxServer.io's Docker implementation.

The resulting image is assembled from:

- the original LinuxServer.io `docker-ddclient` build environment at a published LinuxServer.io release;
- an official published ddclient release;
- the existing `DDCLIENT_VERSION` build mechanism provided by LinuxServer.io.

The purpose of this repository is to automate the selection, verification, building, and publication of the newest published ddclient release, including pre-releases.

Upstream projects:

- [ddclient/ddclient](https://github.com/ddclient/ddclient)
- [linuxserver/docker-ddclient](https://github.com/linuxserver/docker-ddclient)

Issues specific to ddclient itself or the LinuxServer.io container should be reported to the corresponding upstream project.

Issues specific to the automation or images published by this repository should be reported here.

## Architectures

The images produced by this repository currently follow the architecture built by this repository's GitHub Actions workflow.

They should not be assumed to provide the same multi-architecture manifest as the official LinuxServer.io image unless explicitly published as such.

If multi-architecture support is required, use the official LinuxServer.io image or verify that the required architecture is available in this repository's GHCR package.

## License

The automation and other original content in this repository are licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE).

The resulting Docker images contain software from upstream projects under their respective licenses, including:

- **LinuxServer.io docker-ddclient** — GNU General Public License v3.0
- **ddclient** — GNU General Public License v2.0 or later

Copyright and license terms of the upstream projects remain with their respective copyright holders.

This repository does not relicense or replace the licenses of upstream software.

## Disclaimer

This is an independent project and is **not affiliated with, endorsed by, or maintained by LinuxServer.io or the ddclient project**.

Pre-release versions of ddclient may contain bugs, regressions, or incomplete functionality.

If stability is more important than access to the newest published ddclient release, consider using the official LinuxServer.io image or pin this image to a version that you have tested.
