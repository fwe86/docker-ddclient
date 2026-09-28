# syntax=docker/dockerfile:1

ARG UPSTREAM_IMAGE
FROM ${UPSTREAM_IMAGE}

ARG IMAGE_VERSION
ARG BUILD_DATE
ARG DDCLIENT_VERSION
ARG LSIO_TAG
ARG LSIO_COMMIT
ARG PROJECT_COMMIT

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
      io.github.fwe86.linuxserver.revision="${LSIO_COMMIT}"

COPY root/etc/s6-overlay/s6-rc.d/init-adduser/branding \
     /etc/s6-overlay/s6-rc.d/init-adduser/branding

RUN printf '%s\n' \
      "fwe86/docker-ddclient version: ${IMAGE_VERSION}" \
      "Build-date: ${BUILD_DATE}" \
      "ddclient release: ${DDCLIENT_VERSION}" \
      "LinuxServer.io docker-ddclient source: ${LSIO_TAG}" \
      "LinuxServer.io source commit: ${LSIO_COMMIT}" \
      "Project revision: ${PROJECT_COMMIT}" \
      "Independent project; not affiliated with, endorsed by, or maintained by LinuxServer.io." \
      > /build_version
