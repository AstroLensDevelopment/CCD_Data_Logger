# GitHub Actions APK Build Guide

Your project is now set up to automatically build Android APKs using GitHub Actions!

## Setup Steps

### 1. Create GitHub Repository

```bash
cd /Users/amatsch/CCD_Data_Logger

# Initialize git (if not already done)
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: CCD Data Logger with STM32 support"
```

### 2. Push to GitHub

**Option A: Create new repository on GitHub.com**

1. Go to https://github.com/new
2. Repository name: `CCD_Data_Logger` (or your choice)
3. Keep it Public (required for free Actions) or Private (if you have paid plan)
4. Don't initialize with README (we have one)
5. Click "Create repository"

**Option B: Use GitHub CLI (if installed)**

```bash
gh repo create CCD_Data_Logger --public --source=. --remote=origin
```

### 3. Add Remote and Push

```bash
# Add your GitHub repo as remote (replace with your username)
git remote add origin https://github.com/YOUR_USERNAME/CCD_Data_Logger.git

# Push to GitHub
git push -u origin main
```

If your default branch is `master` instead of `main`:
```bash
git push -u origin master
```

### 4. GitHub Actions Will Automatically Build

Once pushed, GitHub Actions will:
- ✅ Detect the workflow file
- ✅ Start building your APK automatically
- ✅ Take about 20-30 minutes for first build
- ✅ Store APK as an artifact for 30 days

## Download Your APK

### From GitHub Actions:

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Click on the latest workflow run
4. Scroll down to "Artifacts" section
5. Download `ccddatalogger-apk.zip`
6. Extract the APK file

### Using Command Line:

```bash
# Install GitHub CLI if needed
brew install gh

# Login to GitHub
gh auth login

# Download latest artifact
gh run download --repo YOUR_USERNAME/CCD_Data_Logger
```

## Manual Build Trigger

You can manually trigger a build without pushing code:

1. Go to "Actions" tab on GitHub
2. Select "Build Android APK" workflow
3. Click "Run workflow" button
4. Select branch and click "Run workflow"

## Create Release with APK

To create a release with the APK attached:

```bash
# Create and push a tag
git tag v1.0.0
git push origin v1.0.0
```

The APK will automatically be attached to the GitHub release!

## Troubleshooting

### Build fails?

Check the Actions logs:
1. Go to Actions tab
2. Click on the failed run
3. Click on "build" job
4. Expand failed step to see error

Common issues:
- **Out of disk space**: GitHub provides 14GB, usually enough
- **Timeout**: Free tier has 6-hour limit (usually completes in 30 min)
- **Dependencies**: Check if buildozer.spec has correct requirements

### APK not appearing?

- Wait for full build completion (20-30 minutes first time)
- Check if workflow completed successfully (green checkmark)
- Ensure you're looking at the latest run

## Subsequent Builds

After first build, GitHub caches dependencies:
- **Build time**: 5-10 minutes
- **Triggered by**: Every push to main/master branch
- **Artifact retention**: 30 days

## Local Development

Continue developing locally and push changes:

```bash
# Make your changes
git add .
git commit -m "Add new feature"
git push

# GitHub Actions will build automatically!
```

## Advanced: Build Matrix

To build for multiple architectures, edit `.github/workflows/build-apk.yml`:

```yaml
strategy:
  matrix:
    arch: [armeabi-v7a, arm64-v8a, x86, x86_64]
```

## Cost

- **Public repositories**: FREE unlimited builds
- **Private repositories**: 
  - Free tier: 2000 minutes/month
  - Pro: 3000 minutes/month
  - Typical build: 25 minutes

## Summary

✅ Push code → GitHub builds APK automatically
✅ Download from Actions artifacts
✅ Create releases with tags
✅ No local build environment needed!
