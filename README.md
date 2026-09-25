# docker-ddclient

Automated Docker builds of [ddclient](https://github.com/ddclient/ddclient) based on the official [LinuxServer.io ddclient Docker repository](https://github.com/linuxserver/docker-ddclient).

The purpose of this repository is to provide an up-to-date LinuxServer.io-based ddclient image that can also use **ddclient pre-releases**.

## Why does this repository exist?

The official LinuxServer.io ddclient image determines the latest stable ddclient release through GitHub's `releases/latest` API when no explicit version is supplied during the build.

GitHub does not consider pre-releases such as release candidates (`rc`) to be the latest stable release.

This can result in a newer published ddclient release being available while the official LinuxServer.io image still uses the previous stable version.

This repository solves that problem without maintaining a custom Dockerfile or modifying the LinuxServer.io container structure.

## How it works

The GitHub Actions workflow periodically checks two upstream projects:

- [ddclient/ddclient](https://github.com/ddclient/ddclient)
- [linuxserver/docker-ddclient](https://github.com/linuxserver/docker-ddclient)

For ddclient, the newest **published release** is selected, including pre-releases such as release candidates.

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
```

No LinuxServer.io Dockerfile or container files are copied into this repository.

Each build checks out the original LinuxServer.io repository at the detected release tag and builds it unchanged.

## Automatic builds

The workflow runs periodically and determines:

1. the latest published LinuxServer.io `docker-ddclient` release;
2. the latest published ddclient release, including pre-releases;
3. whether an image for this exact combination already exists.

If the image already exists, no build is performed.

If either upstream project publishes a relevant new release, a new combination is detected and automatically built.

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

Always points to the newest successfully built combination.

### ddclient version

```text
ghcr.io/fwe86/docker-ddclient:v4.0.1-rc.1
```

Points to the newest LinuxServer.io build created with this specific ddclient version.

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

This is the most precise tag to use when reproducibility is important.

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

This file represents the **last successfully built and published upstream combination**.

It is only updated after:

1. the Docker image has been built successfully;
2. the resulting ddclient version has been verified;
3. all image tags have been successfully pushed to GHCR.

This also provides a transparent history of upstream changes through the repository's Git history.

## Verification

Before an image is published, the workflow performs several checks.

### LinuxServer.io release

The workflow verifies that the checked-out Git commit corresponds to the detected LinuxServer.io release tag.

A mismatch causes the build to fail.

### ddclient version

After building the image, ddclient is executed inside the resulting container:

```bash
ddclient --version
```

The reported version must match the detected upstream ddclient release.

A mismatch prevents the image from being published.

## Usage

The image retains the LinuxServer.io container structure and configuration.

Example:

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

For configuration and general container usage, refer to the official LinuxServer.io documentation:

[LinuxServer.io ddclient documentation](https://docs.linuxserver.io/images/docker-ddclient/)

## Relationship to LinuxServer.io and ddclient

This repository does **not** maintain a fork of ddclient or LinuxServer.io's Docker implementation.

The image is assembled from:

- the original LinuxServer.io `docker-ddclient` build environment;
- an official published ddclient release;
- the existing `DDCLIENT_VERSION` mechanism provided by LinuxServer.io.

The purpose of this repository is solely to automate selecting and building the newest published ddclient release, including pre-releases.

For upstream issues, documentation, and source code, see:

- [ddclient/ddclient](https://github.com/ddclient/ddclient)
- [linuxserver/docker-ddclient](https://github.com/linuxserver/docker-ddclient)

## Disclaimer

This is an independent project and is not affiliated with or maintained by LinuxServer.io or the ddclient project.

Pre-release versions of ddclient may contain bugs or incomplete functionality. If stability is more important than access to the newest release, use the official LinuxServer.io image or pin this image to a known working version.
