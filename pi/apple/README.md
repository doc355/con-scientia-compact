# PI — Apple client (iPhone/iPad, Apple Watch, Apple Vision Pro)

Branch `pi/apple`, cut from `pi/build` (base `eef97cb`). Talks only to the PI Core Gateway (`pi/gateway/pi_gateway.py`).
Simulator builds only. No signing team, no Apple Developer resources, no Apple account used.

## What's built

| Piece | Where | Notes |
|---|---|---|
| `PIKit` (Swift package) | `PIKit/Sources/PIKit` | `GatewayClient` (async/await): `health()`, `chat(_:)` / `ask(_:)`, `models()`, `createJob(kind:payload:)`, `jobs(kind:)`, `job(id:)`, `addEvent(jobID:state:detail:)`, `flushQueue()`. Codable models (`Models.swift`). `GatewayError` maps 400/401/404/502/503/other plus transport errors (offline). |
| Token | `Settings.swift` | `KeychainTokenStore` (service `ai.polstar.pi.gateway`, account `bearer-token`). Never in UserDefaults, never in source. |
| Settings | `Settings.swift` | Gateway URL (default `http://project-iris-1:8784`) and model (default `ollama/gpt-oss:20b`) in UserDefaults keys `PIGatewayURL` / `PIModel`. |
| Offline queue | `OfflineQueue.swift` | FIFO, JSON file in Application Support. POSTs that fail with a transport error are queued, then retried in order on refresh. Kept on offline/401; dropped after any other HTTP reply. |
| VTT | `VoiceInput.swift` | `SFSpeechRecognizer` + `AVAudioEngine`. `requiresOnDeviceRecognition` when supported. Requests speech and mic permission. watchOS has no SFSpeechRecognizer, so the watch uses system dictation (`TextFieldLink`). |
| Read aloud | `Speaker.swift` | `AVSpeechSynthesizer`. |
| Shared UI (`PIUI`) | `PIKit/Sources/PIUI` | `CasualView` (launch screen), `ChatView`, `JobsView`, `SettingsView` (URL, token, model picker from `/v1/models`), `VoiceTextField` (mic button on every text input; the token field is a `SecureField` with no dictation, on purpose). |
| Apps | `Apps/iOS`, `Apps/watchOS`, `Apps/visionOS` | `PI` (universal iPhone+iPad), `PIWatch` (standalone watchOS app), `PIVision` (window, gateway only). All open on `PIRootView` → `CasualView`. Info.plist usage strings for mic, speech recognition and local network. |
| UI tests | `Apps/UITests` | `PIUITests` (iOS): launch screen, `performAccessibilityAudit()`, the same audit at AX-XXXL Dynamic Type, and Chat ask → answer shown on Casual View. |
| Project | `project.yml` → `PI.xcodeproj` | XcodeGen 2.46.0. The generated project is checked in. Regenerate with `xcodegen generate`. |

Casual View: Talk button (tap → speak → chat → answer shown and spoken), gateway health with per-backend status, offline-queue count, latest question/answer, recent jobs (state shown by symbol AND word, never color alone), then Chat / Jobs / Settings.

Accessibility: every control has a label and a hint. Only text styles are used, no fixed font sizes. Status uses symbol + text. `largeHitTarget()` gives a minimum of 44pt (iOS/visionOS). Reduce Motion: the app has no custom animations; `accessibilityReduceMotion` is read in `CasualView`, but nothing currently needs to change for it. Honest note: nothing animation-related was tested.

## Verify (run 2026-10-18 on macOS 26.6.2, Apple M4 Pro VM, Xcode 26.6 17F113, Swift 6.3.3)

Runtimes: iOS 26.5 + 27.0 were preinstalled. watchOS 26.5 and visionOS 26.5 were installed with `xcodebuild -downloadPlatform watchOS|visionOS`.

| Check | Command | Result |
|---|---|---|
| PIKit unit tests | `cd PIKit && swift test` | **PASS**: `Executed 22 tests, with 0 failures (0 unexpected)` |
| iOS Simulator build | `xcodebuild build -project PI.xcodeproj -scheme PI -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO` | **PASS**: `** BUILD SUCCEEDED **` |
| watchOS Simulator build | `... -scheme PIWatch -destination 'generic/platform=watchOS Simulator' ...` | **PASS**: `** BUILD SUCCEEDED **` |
| visionOS Simulator build | `... -scheme PIVision -destination 'generic/platform=visionOS Simulator' ...` | **PASS**: `** BUILD SUCCEEDED **` |
| UI tests + a11y audit, iPhone 17 (iOS 26.5) | `TEST_RUNNER_PI_TEST_TOKEN=<token> xcodebuild test -project PI.xcodeproj -scheme PI -destination 'platform=iOS Simulator,id=<iPhone 17>'` | **PASS**: 4 tests, 0 failures, `** TEST SUCCEEDED **`, `AUDIT ISSUE COUNT: 0` |
| UI tests + a11y audit, iPad Pro 13-inch | same, iPad destination | **PASS**: 4 tests, 0 failures, `** TEST SUCCEEDED **`, `AUDIT ISSUE COUNT: 0` |
| Casual View on Watch (Series 11) | `simctl install` + `simctl launch ai.polstar.pi.watch -PIGatewayURL http://127.0.0.1:8784 -PISeedToken <token>` | **PASS (visual)**: `screenshots/watch-casual-online.png`. With the default URL (no Tailscale in this VM) it correctly shows "Gateway offline": `watch-casual-default-url-offline.png`. No automated a11y audit on watch (the XCUITest target is iOS-only). |
| visionOS launch | `simctl erase/boot/install/launch ai.polstar.pi.vision` (4 erase/boot attempts, one with Simulator.app open) | **NOT VERIFIED**. visionOS: BUILD SUCCEEDED, launch NOT verified (SurfBoard crash in VM, exit -9). `simctl launch` returns a pid, but the app never appears in `launchctl list`. SurfBoard restarts with last exit `-9` (pids 14881 → 15066 across the launch), and one launch failed outright with "The system shell (SurfBoard:11205) probably crashed." Screenshots only ever show the boot logo or the empty room: `vision-environment-NO-APP.png`, `vision-final-attempt-NO-APP.png`. |

Test setup for the UI tests and screenshots: the real `pi/gateway/pi_gateway.py` ran locally (`PI_HOST=127.0.0.1 PI_PORT=8784`, a random `PI_TOKEN`) with an OpenAI-compatible stub standing in for Ollama on `127.0.0.1:11434`. The stub answers `[stub backend] I heard: …`. The stub and token stay outside the repo. The UI test passes the token in through the `-PISeedToken` launch argument, which writes it to the Keychain.

Audit history (append-only): iPhone run 1 had 10 issues (contrast on default section headers, Dynamic Type). Run 2: 5. Run 3: 2. Run 4: 1. Run 5: 0. iPad run 1 had 3 issues ("Contrast nearly passed" with element nil, plus Dynamic Type "partially unsupported" on the Jobs/Settings nav labels). iPad run 2: 0. Fixes: an explicit `SectionHeader` (primary color, `.headerProminence(.increased)`), no `.secondary` foreground, `fixedSize(vertical:)` on wrapping text, and explicit `accessibilityLabel` on the answer text and nav labels. Caveat: the label change is what cleared the "Dynamic Type partially unsupported" findings, which suggests the audit's heuristic, not a layout change, was the cause. The AX-XXXL audit passes, and its screenshots are `iphone-casual-AXXXL.png` / `ipad-casual-AXXXL.png`.

Screenshots (`screenshots/`): `iphone-casual.png`, `ipad-casual.png` (exported from the passing XCUITest result bundles), `watch-casual-online.png`, `watch-casual.png` (earlier run), plus the visionOS NO-APP captures above.

## Left for Christopher

1. **Signing team**: set `DEVELOPMENT_TEAM` in `project.yml` (currently `""`, ad-hoc `-` identity), then `xcodegen generate`.
2. **Bundle IDs**: currently `ai.polstar.pi.app`, `ai.polstar.pi.watch`, `ai.polstar.pi.vision`, `ai.polstar.pi.uitests` (prefix `ai.polstar.pi`). Register them, or change them, in the Apple Developer account. Keychain access group / App Group if the watch should share the phone's token (today each app stores its own).
3. **TestFlight**: App Store Connect records, app icons (none yet), version/build numbers, archive + upload.
4. **visionOS**: run on a Mac whose visionOS simulator shell works (or on device) and confirm Casual View shows in the window.
5. **Watch companion**: decide whether `PIWatch` stays standalone or gets embedded in the iOS app.
6. Visual polish (deliberately skipped).

## Notes log (append-only)

- 2026-10-18: Commit `e760838` (WIP) contained `screenshots/vision-casual.png`, which was **mislabeled**. It showed the visionOS system room, not Casual View. It was renamed to `vision-environment-NO-APP.png` in the next commit. The original commit is left as is.
