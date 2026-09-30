#!/usr/bin/env bash
set -euo pipefail

: "${BASE_IMAGE_PINNED:?BASE_IMAGE_PINNED is required}"
: "${BASE_RELEASE:?BASE_RELEASE is required}"
: "${SOURCE_DIR:?SOURCE_DIR is required}"
: "${WORK_DIR:?WORK_DIR is required}"
: "${GITHUB_ENV:?GITHUB_ENV is required}"

mkdir -p "$SOURCE_DIR" "$WORK_DIR"
BASE_REPO="$WORK_DIR/docker-baseimage-alpine"
S6_REPO="$WORK_DIR/s6-overlay"
MODS_REPO="$WORK_DIR/docker-mods"
EMBEDDED="$WORK_DIR/linuxserver-base-embedded"
rm -rf "$BASE_REPO" "$S6_REPO" "$MODS_REPO" "$EMBEDDED"

fetch_exact_tag() {
  local repo_url="$1" tag="$2" dest="$3"
  git init -q "$dest"
  git -C "$dest" remote add origin "$repo_url"
  git -C "$dest" fetch -q --depth=1 origin "refs/tags/${tag}:refs/tags/${tag}"
  git -C "$dest" checkout -q --detach "refs/tags/${tag}"
}

# Keep the fetch at top level instead of hiding it in command substitution.
# Bash disables errexit inside command substitutions unless inherit_errexit is
# enabled; a failed fetch could otherwise continue into checkout/rev-parse and
# obscure the real failure.
fetch_exact_tag \
  https://github.com/linuxserver/docker-baseimage-alpine.git \
  "$BASE_RELEASE" "$BASE_REPO"
BASE_COMMIT="$(git -C "$BASE_REPO" rev-parse HEAD)"

git -C "$BASE_REPO" archive \
  --format=tar.gz \
  --prefix="linuxserver-docker-baseimage-alpine-${BASE_RELEASE}/" \
  -o "$SOURCE_DIR/linuxserver-docker-baseimage-alpine-${BASE_RELEASE}.tar.gz" \
  "$BASE_RELEASE"

git -C "$BASE_REPO" show "${BASE_RELEASE}:Dockerfile" > "$SOURCE_DIR/Dockerfile-linuxserver-baseimage-alpine"
for candidate in LICENSE LICENSE.md COPYING COPYING.md; do
  if git -C "$BASE_REPO" cat-file -e "${BASE_RELEASE}:${candidate}" 2>/dev/null; then
    git -C "$BASE_REPO" show "${BASE_RELEASE}:${candidate}" > "$SOURCE_DIR/LICENSE-linuxserver-docker-baseimage-alpine"
    break
  fi
done
[[ -s "$SOURCE_DIR/LICENSE-linuxserver-docker-baseimage-alpine" ]] || {
  echo "No license file found in LinuxServer.io base-image source tag ${BASE_RELEASE}" >&2
  exit 1
}

S6_VERSION="$(sed -nE 's/^[[:space:]]*ARG[[:space:]]+S6_OVERLAY_VERSION="?([^"[:space:]]+)"?.*/\1/p' \
  "$SOURCE_DIR/Dockerfile-linuxserver-baseimage-alpine" | head -n1)"
[[ -n "$S6_VERSION" ]] || {
  echo "Could not determine S6_OVERLAY_VERSION from exact LinuxServer.io base-image Dockerfile" >&2
  exit 1
}

S6_TAG="v${S6_VERSION}"
fetch_exact_tag https://github.com/just-containers/s6-overlay.git "$S6_TAG" "$S6_REPO"
S6_COMMIT="$(git -C "$S6_REPO" rev-parse HEAD)"
[[ -f "$S6_REPO/conf/versions" ]] || {
  echo "s6-overlay ${S6_TAG} was fetched but conf/versions is missing from the checked-out worktree" >&2
  exit 1
}
git -C "$S6_REPO" archive \
  --format=tar.gz \
  --prefix="s6-overlay-${S6_TAG}/" \
  -o "$SOURCE_DIR/s6-overlay-${S6_TAG}.tar.gz" \
  "$S6_TAG"
for candidate in LICENSE LICENSE.md COPYING COPYING.md; do
  if git -C "$S6_REPO" cat-file -e "${S6_TAG}:${candidate}" 2>/dev/null; then
    git -C "$S6_REPO" show "${S6_TAG}:${candidate}" > "$SOURCE_DIR/LICENSE-s6-overlay"
    break
  fi
done
[[ -s "$SOURCE_DIR/LICENSE-s6-overlay" ]] || {
  echo "No license file found in s6-overlay source tag ${S6_TAG}" >&2
  exit 1
}

# The base image downloads several LinuxServer.io helper scripts directly from
# docker-mods.  Those scripts are already source-form shell code.  Preserve the
# exact bytes that are actually distributed in the pinned base image, together
# with the docker-mods GPL license and repository provenance.
mkdir -p "$EMBEDDED/files"
CID="$(docker create "$BASE_IMAGE_PINNED")"
trap 'docker rm -f "$CID" >/dev/null 2>&1 || true' EXIT
# docker cp works with a stopped container created from the pinned base image.
for path in \
  /docker-mods \
  /etc/s6-overlay/s6-rc.d/init-mods-package-install/run \
  /etc/s6-overlay/s6-rc.d/init-mods-end/run \
  /etc/s6-overlay/s6-rc.d/init-mods/run \
  /usr/bin/lsiown \
  /usr/bin/with-contenv; do
  target="$EMBEDDED/files$path"
  if [[ ! -e "$target" ]]; then
    mkdir -p "$(dirname "$target")"
    docker cp "$CID:$path" "$target" >/dev/null 2>&1 || rmdir -p --ignore-fail-on-non-empty "$(dirname "$target")" 2>/dev/null || true
  fi
done

git clone -q --depth=1 --branch mod-scripts https://github.com/linuxserver/docker-mods.git "$MODS_REPO"
MODS_COMMIT="$(git -C "$MODS_REPO" rev-parse HEAD)"
for candidate in LICENSE LICENSE.md COPYING COPYING.md; do
  if [[ -f "$MODS_REPO/$candidate" ]]; then
    cp "$MODS_REPO/$candidate" "$EMBEDDED/LICENSE-linuxserver-docker-mods"
    break
  fi
done
if [[ ! -s "$EMBEDDED/LICENSE-linuxserver-docker-mods" ]]; then
  git -C "$MODS_REPO" fetch -q --depth=1 origin master:refs/remotes/origin/master || true
  for candidate in LICENSE LICENSE.md COPYING COPYING.md; do
    if git -C "$MODS_REPO" cat-file -e "origin/master:${candidate}" 2>/dev/null; then
      git -C "$MODS_REPO" show "origin/master:${candidate}" > "$EMBEDDED/LICENSE-linuxserver-docker-mods"
      break
    fi
  done
fi
[[ -s "$EMBEDDED/LICENSE-linuxserver-docker-mods" ]] || {
  echo "No license file found in linuxserver/docker-mods" >&2
  exit 1
}
cat > "$EMBEDDED/SOURCE_INFO.txt" <<EOF
Pinned base image: ${BASE_IMAGE_PINNED}
LinuxServer.io base source tag: ${BASE_RELEASE}
LinuxServer.io base source commit: ${BASE_COMMIT}
s6-overlay tag: ${S6_TAG}
s6-overlay commit: ${S6_COMMIT}
linuxserver/docker-mods branch: mod-scripts
linuxserver/docker-mods observed commit for license provenance: ${MODS_COMMIT}

The files/ directory contains exact source-form helper scripts copied from the
pinned base image.  They are preserved byte-for-byte from the distributed image
because the upstream Dockerfile retrieves them from a moving branch.
EOF

tar -C "$EMBEDDED" -czf "$SOURCE_DIR/linuxserver-base-embedded-scripts.tar.gz" .

cat > "$SOURCE_DIR/BASE_SOURCE_INFO.txt" <<EOF
LinuxServer.io base image (pinned): ${BASE_IMAGE_PINNED}
LinuxServer.io base source release: ${BASE_RELEASE}
LinuxServer.io base source commit: ${BASE_COMMIT}
s6-overlay release: ${S6_TAG}
s6-overlay source commit: ${S6_COMMIT}
linuxserver/docker-mods observed commit: ${MODS_COMMIT}
EOF

{
  echo "LSIO_BASE_COMMIT=${BASE_COMMIT}"
  echo "S6_OVERLAY_VERSION=${S6_VERSION}"
  echo "S6_OVERLAY_COMMIT=${S6_COMMIT}"
  echo "DOCKER_MODS_COMMIT=${MODS_COMMIT}"
} >> "$GITHUB_ENV"

trap - EXIT
docker rm -f "$CID" >/dev/null 2>&1 || true
