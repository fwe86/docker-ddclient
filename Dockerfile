# syntax=docker/dockerfile:1

ARG UPSTREAM_IMAGE
FROM ${UPSTREAM_IMAGE}

ARG IMAGE_VERSION
ARG BUILD_DATE
ARG DDCLIENT_VERSION
ARG LSIO_TAG
ARG LSIO_COMMIT
ARG PROJECT_COMMIT
ARG COMPLIANCE_RELEASE
ARG LSIO_BASE_IMAGE
ARG LSIO_BASE_DIGEST
ARG LSIO_BASE_RELEASE
ARG LSIO_BASE_COMMIT

ENV LSIO_FIRST_PARTY=false

LABEL maintainer="fwe86" \
      build_version="fwe86/docker-ddclient version:- ${IMAGE_VERSION} Build-date:- ${BUILD_DATE}" \
      org.opencontainers.image.authors="fwe86" \
      org.opencontainers.image.vendor="fwe86" \
      org.opencontainers.image.title="docker-ddclient" \
      org.opencontainers.image.description="Independent ddclient container image based on LinuxServer.io docker-ddclient" \
      org.opencontainers.image.url="https://github.com/fwe86/docker-ddclient" \
      org.opencontainers.image.source="https://github.com/fwe86/docker-ddclient" \
      org.opencontainers.image.documentation="https://github.com/fwe86/docker-ddclient#readme" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${PROJECT_COMMIT}" \
      io.github.fwe86.ddclient.version="${DDCLIENT_VERSION}" \
      io.github.fwe86.linuxserver.release="${LSIO_TAG}" \
      io.github.fwe86.linuxserver.revision="${LSIO_COMMIT}" \
      io.github.fwe86.linuxserver.base.image="${LSIO_BASE_IMAGE}" \
      io.github.fwe86.linuxserver.base.digest="${LSIO_BASE_DIGEST}" \
      io.github.fwe86.linuxserver.base.release="${LSIO_BASE_RELEASE}" \
      io.github.fwe86.linuxserver.base.revision="${LSIO_BASE_COMMIT}" \
      io.github.fwe86.compliance.release="${COMPLIANCE_RELEASE}" \
      io.github.fwe86.compliance.url="https://github.com/fwe86/docker-ddclient/releases/tag/${COMPLIANCE_RELEASE}"

# LinuxServer.io explicitly requires downstream images to provide their own
# branding.  Keep the path expected by the inherited s6 init service, but
# replace the content with this project's identity.
COPY root/etc/s6-overlay/s6-rc.d/init-adduser/branding \
     /etc/s6-overlay/s6-rc.d/init-adduser/branding

RUN printf '%s\n' \
      "fwe86/docker-ddclient version:- ${IMAGE_VERSION}" \
      "Build-date:- ${BUILD_DATE}" \
      "ddclient version:- ${DDCLIENT_VERSION}" \
      "LinuxServer.io docker-ddclient release:- ${LSIO_TAG}" \
      "LinuxServer.io docker-ddclient revision:- ${LSIO_COMMIT}" \
      "LinuxServer.io base release:- ${LSIO_BASE_RELEASE}" \
      "LinuxServer.io base digest:- ${LSIO_BASE_DIGEST}" \
      "Compliance source release:- ${COMPLIANCE_RELEASE}" \
      > /build_version
