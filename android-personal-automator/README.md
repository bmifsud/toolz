# AIEF Android Personal Automator (POC)

An extensible, user-supervised Android automation companion.

## First milestone
- Show a floating glowing-ball pointer and persistent Pause / Resume / Stop controls.
- Open the GitHub pull request https://github.com/bmifsud/POC-ARTRIOUT/pull/299 for read-only inspection.
- Never approve, merge, type credentials, or modify GitHub/Render in the demo.
- Future Android AccessibilityService-based interaction must be explicitly enabled by the device owner in Android Settings; no hidden operation.

## Architecture
Keep command interpretation independent from execution. Commands become typed, allowlisted actions. The executor checks permissions, displays the action to the user, and records the result. Sensitive or write actions require explicit approval. No ChatGPT Go subscription or secret is embedded in the Android app.

## Current state
This branch establishes an Android Studio Kotlin starter and safe read-only GitHub deep-link demo. It does **not** yet automate screen taps, draw an overlay, or implement an AccessibilityService. Those features need an on-device permission and safety review.

## Build
Open this folder as an Android Studio project. Use Android Studio's installed Gradle and Android SDK to build and run. No CI/build verification has been performed here.
