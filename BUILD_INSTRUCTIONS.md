# Building Android APK on macOS

Since you're on macOS, you have several options to build the Android APK:

## Option 1: Use Docker (Recommended for macOS)

1. **Install Docker Desktop** for macOS if not already installed:
   https://www.docker.com/products/docker-desktop

2. **Run buildozer in Docker container:**
   ```bash
   cd /Users/amatsch/CCD_Data_Logger
   
   # Pull buildozer Docker image
   docker pull kivy/buildozer
   
   # Build APK using Docker
   docker run --rm -v "$PWD":/home/user/hostcwd kivy/buildozer \
       android debug
   ```

3. The APK will be created in `bin/` directory

## Option 2: Use Linux VM

1. **Install VirtualBox or VMware**
2. **Create Ubuntu 22.04 VM** (recommended: 4GB RAM, 50GB disk)
3. **Copy project to VM**
4. **Run build script:**
   ```bash
   cd /path/to/CCD_Data_Logger
   chmod +x build_apk.sh
   ./build_apk.sh
   ```

## Option 3: Use Cloud Build Service

1. **GitHub Actions** (automated builds):
   - Push code to GitHub
   - Set up GitHub Actions workflow
   - Download APK from artifacts

2. **Google Colab** (free, web-based):
   - Upload project to Google Drive
   - Run buildozer in Colab notebook
   - Download APK

## Option 4: Remote Linux Server

If you have access to a Linux server:
```bash
# Copy project to server
scp -r /Users/amatsch/CCD_Data_Logger user@server:/path/

# SSH to server
ssh user@server

# Build
cd /path/CCD_Data_Logger
chmod +x build_apk.sh
./build_apk.sh
```

## Quick Docker Build (If Docker is installed)

```bash
cd /Users/amatsch/CCD_Data_Logger

# One-line build command
docker run --rm -v "$PWD":/home/user/hostcwd kivy/buildozer android debug

# APK will be in: bin/ccddatalogger-1.0.0-arm64-v8a_armeabi-v7a-debug.apk
```

## Build Time Expectations

- **First build**: 20-30 minutes (downloads SDK, NDK, dependencies)
- **Subsequent builds**: 2-5 minutes
- **APK size**: ~30-50 MB

## After Building

Install APK on Android device:
```bash
# Via ADB
adb install bin/ccddatalogger-*.apk

# Or copy APK to device and install manually
```

## Troubleshooting

### Docker not installed?
```bash
brew install --cask docker
```

### Need to clean build?
```bash
rm -rf .buildozer bin
```

### Build fails with memory error?
Increase Docker memory allocation in Docker Desktop preferences.
