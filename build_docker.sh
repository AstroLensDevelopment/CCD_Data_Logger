#!/bin/bash
# Quick APK build using Docker on macOS
# 
# Prerequisites: Install Docker Desktop for Mac
# https://www.docker.com/products/docker-desktop

echo "=========================================="
echo "CCD Data Logger - Docker Build for macOS"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    echo ""
    echo "Please install Docker Desktop for Mac:"
    echo "1. Download from: https://www.docker.com/products/docker-desktop"
    echo "2. Install and start Docker Desktop"
    echo "3. Run this script again"
    echo ""
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running"
    echo ""
    echo "Please start Docker Desktop and try again"
    echo ""
    exit 1
fi

echo "Docker is ready!"
echo ""
echo "Building APK using buildozer Docker image..."
echo "This will take 20-30 minutes on first run..."
echo ""

# Pull buildozer image
echo "Pulling buildozer image..."
docker pull kivy/buildozer

# Build APK
echo ""
echo "Starting build..."
echo ""
docker run --rm -v "$(pwd)":/home/user/hostcwd kivy/buildozer android debug

# Check if APK was created
if [ -f "bin/"*.apk ]; then
    echo ""
    echo "=========================================="
    echo "Build Complete!"
    echo "=========================================="
    echo ""
    APK_FILE=$(ls bin/*.apk | head -n 1)
    echo "APK created: $APK_FILE"
    echo "Size: $(du -h "$APK_FILE" | cut -f1)"
    echo ""
    echo "To install on Android device:"
    echo "  1. Copy APK to your device"
    echo "  2. Enable 'Install from unknown sources'"
    echo "  3. Tap the APK to install"
    echo ""
    echo "Or use ADB:"
    echo "  adb install '$APK_FILE'"
    echo ""
else
    echo ""
    echo "ERROR: APK file not found"
    echo "Check the build output above for errors"
    exit 1
fi
