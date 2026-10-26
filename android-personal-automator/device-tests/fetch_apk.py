#!/usr/bin/env python3
"""Fetch the reviewed, successful main-push artifact. Never installs or grants permissions."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

REPO = "bmifsud/toolz"
RUN = 40146989153
COMMIT = "8b5b651f2531baa1a1d5f34d05a0da9eeb8b4330"
ARTIFACT = 12580678663
ZIP_SHA = "3edfa59dec87fd11a3a5c606a4272753a59b78a7db8d34110d1d9aa5bc5865a5"
APK_SHA = "5ce53a5cee8ac47f2ebf962beb8a0b9547ecf3673274e4657663214f562fd8f6"


def api(path):
    return subprocess.check_output(["gh", "api", f"repos/{REPO}/{path}"])


def validate_run(run):
    expected = {
        "id": RUN, "head_sha": COMMIT, "head_branch": "main", "event": "push",
        "status": "completed", "conclusion": "success", "path": ".github/workflows/android.yml",
    }
    if any(run.get(key) != value for key, value in expected.items()):
        raise ValueError("Run identity, source or conclusion differs from reviewed build")
    for key in ("repository", "head_repository"):
        if run.get(key, {}).get("full_name") != REPO:
            raise ValueError("Unexpected source repository")


def validate_artifact(artifact):
    if (artifact.get("id") != ARTIFACT or artifact.get("name") != "android-debug-apk"
            or artifact.get("expired") is not False
            or artifact.get("digest") != f"sha256:{ZIP_SHA}"
            or artifact.get("workflow_run", {}).get("id") != RUN
            or artifact.get("workflow_run", {}).get("head_sha") != COMMIT):
        raise ValueError("Artifact does not match the reviewed build or has expired")


def unpack(archive):
    if hashlib.sha256(archive).hexdigest() != ZIP_SHA:
        raise ValueError("Artifact ZIP checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        if package.namelist() != ["app-debug.apk"]:
            raise ValueError("Unexpected artifact contents")
        apk = package.read("app-debug.apk")
    if hashlib.sha256(apk).hexdigest() != APK_SHA:
        raise ValueError("APK checksum mismatch")
    return apk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path.home() /
                        f".local/share/toolz-device-test/build-{RUN}/app-debug.apk")
    args = parser.parse_args()
    os.umask(0o077)
    validate_run(json.loads(api(f"actions/runs/{RUN}")))
    validate_artifact(json.loads(api(f"actions/artifacts/{ARTIFACT}")))
    apk = unpack(api(f"actions/artifacts/{ARTIFACT}/zip"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite an existing APK or follow a pre-existing symlink.
    with args.output.open("xb") as output:
        output.write(apk)
    print(f"Verified APK: {args.output}\nSHA256: {APK_SHA}")
    print("Open with Android's package installer; review and approve installation yourself.")


if __name__ == "__main__":
    main()
