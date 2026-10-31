# Tier-2 isolated recovery safety gate (design; not implemented)

Status: **pending**. This document does not authorize extraction or enabling Tier-2 cron.

## Objective
Prove that an encrypted Andronix Debian backup can be decrypted, integrity-checked and recovered into a fresh, isolated destination without touching the live rootfs.

## Required implementation
1. Operate from outer Termux, with the source Debian PRoot stopped. Refuse any destination equal to, inside, or containing the live rootfs, and refuse symlinked destination ancestors.
2. Obtain the encrypted archive from a verified Google Drive object; retain its remote object identity and checksums. Do not print passphrases or persist decrypted tar files.
3. Stream decrypt to a *staging directory* on a filesystem with sufficient free space. Use an independently audited extractor; do **not** pipe the archive to `tar -x` or use `tarfile.extractall` against untrusted members.
4. Accept only expected member names, file/dir/symlink types, and launcher/rootfs layout. Reject absolute archive member paths, empty/dot/dot-dot components, duplicates, unexpected prefixes, hardlinks, devices, FIFOs, sockets, and sparse/unsupported metadata until explicitly supported.
5. Create regular files and directories using directory-file-descriptor-relative operations with no-follow semantics, and enforce that archive-controlled symlinks cannot become parent traversal paths. Consider delayed symlink creation after all regular files/directories, and never follow symlinks during writes.
6. Preserve Debian absolute symlink targets **as link metadata**, not by resolving them against the host. Permit literal backslashes in POSIX filenames (systemd escaping).
7. Reject symlink destinations escaping the isolated Debian rootfs for relative links. Treat the launcher separately. Reject extraction into an existing nonempty directory.
8. Enforce per-file and total expanded-size, member-count and path-length limits based on measured rootfs needs; reject truncated or corrupted streams and verify GPG exit status (not merely the extractor's exit status).
9. After extraction, verify expected launcher, /etc, /usr and required executable/link layout, permissions, and manifest checksums. Do not execute the restored launcher as part of the initial test.
10. Provide cleanup on failure only for the newly created staging directory; never delete pre-existing user paths. Require explicit confirmation before any later live-rootfs replacement.

## Adversarial regression tests
- `../`, absolute paths, empty/dot components, duplicate members
- Symlink before child, child before symlink, chained links, symlink to parent, absolute links
- Hardlink, device, FIFO, socket and unsupported entry types
- systemd literal-backslash filenames
- Missing launcher/rootfs, malformed gzip, truncated archive, GPG authentication failure
- Destination symlink/race attempts, pre-existing nonempty destination, insufficient space
- Large expanded size and member-count exhaustion
- Failure halfway through extraction: no writes outside staging, live rootfs untouched

## Release gates
- Full real-rootfs read-only streaming validation: **PASS, user-reported 2026-10-26, 2088 seconds** (streaming archive structural validation; not a recovery test)
- Isolated recovery implementation and adversarial tests: **pending**
- Verified encrypted cloud object and full decrypt-to-isolated-recovery: **pending**
- Manual recovery procedure reviewed and documented: **pending**
- Tier-2 cron: **must remain disabled**

Tier-1 behavior and scheduling must not be modified by this work.
