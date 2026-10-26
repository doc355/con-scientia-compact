#!/bin/bash
# Build Iris Control into a staging folder, then install to /Applications (additive; replaces only an older Iris Control).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"; ST="$SRC/stage"; A="$ST/Iris Control.app"
rm -rf "$ST"; mkdir -p "$A/Contents/MacOS" "$A/Contents/Resources" "$ST/Iris.iconset"
xcrun swiftc -O -swift-version 5 -framework AppKit "$SRC/main.swift" -o "$A/Contents/MacOS/IrisControl"
"$A/Contents/MacOS/IrisControl" --icon "$ST/Iris.iconset"
iconutil -c icns "$ST/Iris.iconset" -o "$A/Contents/Resources/IrisControl.icns"
cp "/Applications/Project Iris.app/Contents/Resources/project-iris-launch.sh" "$A/Contents/Resources/"
[ -f "$SRC/services.json" ] && cp "$SRC/services.json" "$A/Contents/Resources/"
cat > "$A/Contents/Info.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Iris Control</string><key>CFBundleDisplayName</key><string>Iris Control</string>
<key>CFBundleIdentifier</key><string>com.hifidecant.iriscontrol</string><key>CFBundleExecutable</key><string>IrisControl</string>
<key>CFBundleIconFile</key><string>IrisControl</string><key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string><key>CFBundleVersion</key><string>1</string>
<key>LSMinimumSystemVersion</key><string>13.0</string><key>NSHighResolutionCapable</key><true/>
<key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PL
codesign --force --deep -s - "$A"
echo "built: $A"
