#!/bin/bash
# Build script for CCD Data Logger Android APK
# This script must be run on Linux (Ubuntu/Debian) or WSL

set -e  # Exit on error

echo "=========================================="
echo "CCD Data Logger - Android APK Build"
echo "=========================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "ERROR: This script must be run on Linux or WSL"
    echo "You are currently on: $OSTYPE"
    echo ""
    echo "Options:"
    echo "1. Use a Linux VM (VirtualBox, VMware)"
    echo "2. Use WSL on Windows"
    echo "3. Use Docker with buildozer image"
    echo ""
    exit 1
fi

# Check if buildozer is installed
if ! command -v buildozer &> /dev/null; then
    echo "Buildozer not found. Installing..."
    echo ""
    
    # Install system dependencies
    echo "Installing system dependencies..."
    sudo apt update
    sudo apt install -y git zip unzip openjdk-11-jdk python3-pip autoconf \
        libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
        libtinfo5 cmake libffi-dev libssl-dev
    
    # Install Python dependencies
    echo "Installing Python dependencies..."
    pip3 install --upgrade pip
    pip3 install buildozer cython==0.29.33
    
    echo "Buildozer installed successfully!"
    echo ""
fi

# Clean previous builds
echo "Cleaning previous builds..."
if [ -d ".buildozer" ]; then
    echo "Removing .buildozer directory..."
    rm -rf .buildozer
fi

if [ -d "bin" ]; then
    echo "Removing bin directory..."
    rm -rf bin
fi

echo ""
echo "Starting APK build..."
echo "This will take 15-30 minutes on first build..."
echo ""

# Build debug APK
buildozer android debug

echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""

# Check if APK was created
if [ -f "bin/*.apk" ]; then
    APK_FILE=$(ls bin/*.apk | head -n 1)
    echo "APK created successfully:"
    echo "$APK_FILE"
    echo ""
    echo "File size: $(du -h "$APK_FILE" | cut -f1)"
    echo ""
    echo "To install on device:"
    echo "  adb install $APK_FILE"
    echo ""
    echo "Or copy to your device and install manually"
else
    echo "ERROR: APK file not found in bin/ directory"
    exit 1
fi
