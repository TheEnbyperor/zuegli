#!/usr/bin/env bash

VERSION=$(sentry-cli releases propose-version || exit)

git rev-parse --short HEAD > .git_hash
docker buildx build --platform linux/amd64 --push -t "theenbyperor/vdv-pkpass-django:$VERSION" . || exit