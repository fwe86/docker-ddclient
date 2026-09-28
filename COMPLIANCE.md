# Open-source compliance process

This document describes the source-disclosure and provenance controls used by
`fwe86/docker-ddclient`.

The project is an independent downstream image. It is not an official
LinuxServer.io or ddclient project.

## Principles

The publication workflow follows five rules:

1. **The final image is authoritative.** Package/source collection is based on
   what is actually installed in the built image, not only on what a Dockerfile
   appears to install.
2. **Source is disclosed before object code is published.** The GitHub
   compliance release is created and verified before any GHCR image tag is
   pushed.
3. **Exact image tags are immutable.** An existing
   `<ddclient-release>-ls<LinuxServer-build>` tag is never rebuilt or
   overwritten. There is no force-rebuild path.
4. **Moving upstream references are pinned for each build.** The moving
   LinuxServer.io base-image tag in the exact upstream Dockerfile is resolved to
   its registry digest. A generated Dockerfile changes only that `FROM`
   reference and both the original and generated Dockerfiles are retained.
5. **The build fails closed.** Missing source provenance, missing source input,
   failed checksum validation, missing license files, or failed source-release
   publication stop the workflow before the container image is distributed.

## Direct project and application source

Each compliance release contains:

- the exact project source at the workflow commit;
- the exact LinuxServer.io `docker-ddclient` release source and its license;
- the exact ddclient release source, license, and copyright information;
- the exact project final-stage Dockerfile and branding file;
- exact commit and release metadata in `SOURCE_INFO.txt` and
  `BUILD_INPUTS.json`.

## LinuxServer.io base-image provenance

The upstream LinuxServer.io `docker-ddclient` Dockerfile currently references a
base-image tag rather than an immutable digest. The workflow resolves that tag
before building and records:

- the original base-image reference;
- the pinned registry digest;
- the LinuxServer.io base-image release and source commit;
- the original upstream Dockerfile;
- the mechanically generated pinned Dockerfile;
- a unified diff proving that the `FROM` reference is the intended change.

The corresponding LinuxServer.io base-image source release is archived as part
of the same compliance release.

## Alpine packages

The workflow reads `/lib/apk/db/installed` from the **final built image**.
Therefore inherited packages and packages installed by the LinuxServer.io build
are handled identically.

For every installed APK package it records package name, package version,
architecture, declared license, source-package origin, and the Alpine aports
commit embedded in the package metadata.

For every unique source package the workflow then:

1. fetches the exact aports commit;
2. archives the exact `APKBUILD` directory, including local patches, scripts,
   and other build inputs;
3. runs Alpine's `abuild fetch` against that exact package recipe;
4. downloads the referenced remote source inputs into the bundle;
5. relies on `abuild fetch` to perform the recipe's configured source checksum
   validation;
6. generates an internal SHA-256 manifest.

This is deliberately performed for **all installed Alpine packages**, not only
for packages whose license classifier happens to identify them as copyleft.
That avoids silently omitting a package because of an incomplete license
classification.

Generated files include:

- `ALPINE_PACKAGES.tsv`
- `ALPINE_SOURCE_UNITS.tsv`
- `alpine-corresponding-source-<release>-<arch>.tar.gz`

## CPAN distributions

LinuxServer.io installs some Perl software through CPAN rather than APK. The
workflow discovers installed CPAN distributions through `.packlist` files below
`/usr/local`, determines each installed module version with Perl's
`Module::Metadata`, resolves the exact release through MetaCPAN, and downloads
the corresponding source archive.

If an installed CPAN module cannot be mapped to an exact source archive, the
build stops before publication.

Generated files include:

- `CPAN_COMPONENTS.tsv`
- `cpan-corresponding-source.tar.gz`

## s6-overlay and LinuxServer.io helper scripts

The exact LinuxServer.io base-image source identifies the s6-overlay release
used to construct the image. The workflow archives that exact s6-overlay source
release and its license.

The LinuxServer.io base build also retrieves helper scripts from the
`linuxserver/docker-mods` repository. Because those shell scripts are already
source-form code and the upstream branch reference is moving, the workflow
copies the exact bytes distributed in the pinned base image and bundles them
with repository/license provenance.

## SBOM

An SPDX JSON SBOM is generated from the final image. ddclient is explicitly
added/enriched because it is installed outside Alpine package metadata. Its
version is independently verified by executing `ddclient --version` in the
built container.

The SBOM is an inventory. It is **not** treated as a substitute for source-code
or notice obligations.

## Publication order

The workflow publishes in this order:

```text
Detect exact upstream releases
        ↓
Verify exact LinuxServer.io source tag
        ↓
Resolve LinuxServer.io base tag to digest
        ↓
Collect direct/base source provenance
        ↓
Build upstream with pinned base digest
        ↓
Build independent final image
        ↓
Verify branding, provenance and ddclient version
        ↓
Collect Alpine and CPAN corresponding source
        ↓
Generate/verify SPDX SBOM and SHA256SUMS
        ↓
Create + verify immutable GitHub compliance release
        ↓
Login to GHCR
        ↓
Push mutable aliases
        ↓
Push immutable exact image tag
        ↓
Attach exact registry digest to compliance release
        ↓
Update .upstream
```

A source-collection or source-release failure therefore occurs before object
code is made available from this project's GHCR package.

## Release immutability

A compliance release name contains the exact image tag plus the GitHub Actions
run ID and attempt number:

```text
image-<exact-image-tag>-run-<run-id>-<attempt>
```

Release assets are never overwritten with `--clobber`.

The final image contains labels pointing to that exact compliance release. The
exact GHCR image tag is published only once. Mutable convenience aliases such
as `latest`, `<ddclient-version>`, and `ls<build>` may move to a newer successful
build as expected.

## Verification material

Each release contains `SHA256SUMS` covering the release assets available before
image publication. After the exact GHCR tag is pushed, `IMAGE_DIGESTS.txt` is
attached to the same release and records the immutable registry digest.

The project does not set a single `org.opencontainers.image.licenses` value for
the complete image, because the image is an aggregate of components distributed
under multiple licenses. Component-level license information belongs in the
source material and SBOM.
