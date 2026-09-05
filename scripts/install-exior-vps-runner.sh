#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Falcone747/EXIOR-"
RUNNER_USER="exiorrunner"
RUNNER_DIR="/opt/exior-actions-runner"
RUNNER_LABEL="exior-vps"
TOKEN="${1:-}"

if [[ $EUID -ne 0 ]]; then echo "Run as root." >&2; exit 1; fi
if [[ -z "$TOKEN" ]]; then echo "Usage: bash install-exior-vps-runner.sh <TOKEN>" >&2; exit 2; fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl jq tar ca-certificates git sudo

id "$RUNNER_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$RUNNER_USER"
mkdir -p "$RUNNER_DIR"
chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"

LATEST_TAG="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name)"
VERSION="${LATEST_TAG#v}"
ARCHIVE="actions-runner-linux-x64-${VERSION}.tar.gz"
URL="https://github.com/actions/runner/releases/download/${LATEST_TAG}/${ARCHIVE}"

echo "Installing GitHub Actions runner ${VERSION}..."
rm -rf "$RUNNER_DIR"/*
curl -fL "$URL" -o "/tmp/$ARCHIVE"
tar xzf "/tmp/$ARCHIVE" -C "$RUNNER_DIR"
chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"

cat >/etc/sudoers.d/exiorrunner <<'SUDOERS'
exiorrunner ALL=(root) NOPASSWD: /bin/bash
SUDOERS
chmod 440 /etc/sudoers.d/exiorrunner
visudo -cf /etc/sudoers.d/exiorrunner

# Fixed stable runner name: no locale-sensitive tr expression.
HOST_LABEL="$(hostname)"
RUNNER_NAME="exior-vps-${HOST_LABEL}"

cd "$RUNNER_DIR"
sudo -u "$RUNNER_USER" ./config.sh \
  --url "$REPO_URL" \
  --token "$TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$RUNNER_LABEL" \
  --work _work \
  --unattended \
  --replace

./svc.sh install "$RUNNER_USER"
./svc.sh start
sleep 3
./svc.sh status

echo
echo "EXIOR_VPS_RUNNER_READY"
echo "Runner: $RUNNER_NAME"
echo "Repo:   $REPO_URL"
echo "Label:  $RUNNER_LABEL"
