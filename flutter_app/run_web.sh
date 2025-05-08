#!/usr/bin/env bash
# Script to start the Flutter web app with hot reload
# Usage: ./run_web.sh

# Change to the script's directory
cd "$(dirname "$0")"

# Ensure dependencies are up to date
flutter pub get

# Run the Flutter web app in Chrome with hot reload enabled
flutter run -d chrome 