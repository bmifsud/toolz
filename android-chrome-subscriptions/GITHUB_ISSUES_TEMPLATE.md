# GitHub Issue Submissions (bmifsud/toolz)

The following issues identified during testing have been formatted for GitHub repository `bmifsud/toolz`:

---

### Issue #1: Android Chrome Sandboxing Limits Direct SQLite Access on Non-Rooted Devices
- **Labels**: `bug`, `android`, `sandboxing`, `enhancement`
- **Milestone**: v1.0
- **Description**:
  When attempting to directly read Chrome's internal SQLite databases (`Cookies`, `Login Data`) in `/data/data/com.android.chrome/app_chrome/Default`, the script encounters permission denied errors on non-rooted Android devices due to Android app sandboxing restrictions.
- **Proposed Solution / Workaround**:
  The tool successfully falls back to Chrome DevTools Protocol (CDP) port forwarding (`tcp:9222`) and Android Intent URL launching (`am start`) to inspect active subscription tabs and portals securely.

---

### Issue #2: Omniroute Service Unavailability Handling
- **Labels**: `network`, `error-handling`, `omniroute`
- **Milestone**: v1.0
- **Description**:
  If the local Omniroute instance at `http://localhost:20128` is not active or offline when `auto_sync_omniroute.py` executes, connection refused errors (`URLError`) can halt execution if not caught.
- **Proposed Solution / Workaround**:
  Robust exception handling has been added to catch connection errors gracefully, output actionable troubleshooting steps to the user, and retry or save payloads locally as fallback reports.
