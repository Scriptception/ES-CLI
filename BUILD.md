# Building ES-CLI AppImage

This document explains how to build ES-CLI as an AppImage for Linux x86_64 architecture.

## Prerequisites

- Linux x86_64 system (Ubuntu/Debian recommended)
- Python 3.8 or higher
- pip (Python package manager)
- wget (for downloading appimagetool)
- fuse/libfuse2 (for running AppImages)

### Install dependencies on Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv wget squashfs-tools
```

**Note:** The script can use either `squashfs-tools` (recommended, doesn't require FUSE) or `libfuse2` (for running AppImages directly). Installing `squashfs-tools` is recommended as it doesn't require FUSE.

## Building Locally

### Option 1: Using the build script (Recommended)

Simply run the build script:

```bash
chmod +x build_appimage.sh
./build_appimage.sh
```

The AppImage will be created in `build/ES-CLI-x86_64.AppImage`.

### Option 2: Manual build

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install pyinstaller
```

3. Build with PyInstaller:
```bash
pyinstaller --name ES-CLI --onefile --console --clean \
    --add-data "config.yaml.example:." \
    --hidden-import urwid \
    --hidden-import yaml \
    --hidden-import elasticsearch \
    --hidden-import requests \
    --hidden-import urllib3 \
    main.py
```

4. Create AppDir structure:
```bash
mkdir -p ES-CLI.AppDir/usr/bin
cp dist/ES-CLI ES-CLI.AppDir/usr/bin/
cp config.yaml.example ES-CLI.AppDir/usr/share/ES-CLI/
```

5. Create AppRun:
```bash
cat > ES-CLI.AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/usr/bin/ES-CLI" "$@"
EOF
chmod +x ES-CLI.AppDir/AppRun
```

6. Create desktop file:
```bash
cat > ES-CLI.AppDir/ES-CLI.desktop << 'EOF'
[Desktop Entry]
Name=ES-CLI
Comment=Elasticsearch CLI Tool
Exec=ES-CLI
Icon=ES-CLI
Type=Application
Categories=Utility;Development;
Terminal=true
EOF
```

7. Download and run appimagetool:
```bash
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
ARCH=x86_64 ./appimagetool-x86_64.AppImage ES-CLI.AppDir ES-CLI-x86_64.AppImage
```

## GitHub Actions

The repository includes a GitHub Actions workflow (`.github/workflows/build-appimage.yml`) that automatically builds AppImages when:

1. A tag starting with `v` is pushed (e.g., `v1.0.0`)
2. The workflow is manually triggered

To create a release:

1. Create and push a tag:
```bash
git tag v1.0.0
git push origin v1.0.0
```

2. The workflow will automatically:
   - Build the AppImage
   - Create a GitHub release
   - Attach the AppImage to the release

## Using the AppImage

1. Make it executable:
```bash
chmod +x ES-CLI-x86_64.AppImage
```

2. Run it:
```bash
./ES-CLI-x86_64.AppImage
```

3. (Optional) Move it to a location in your PATH:
```bash
sudo mv ES-CLI-x86_64.AppImage /usr/local/bin/es-cli
```

## Troubleshooting

### "Permission denied" when running AppImage
Make sure the AppImage is executable:
```bash
chmod +x ES-CLI-x86_64.AppImage
```

### "fuse: failed to exec fusermount"
Install fuse/libfuse2:
```bash
sudo apt-get install fuse libfuse2
```

### AppImage doesn't work on newer systems
Some newer Linux distributions use libfuse3 instead of libfuse2. You may need to install libfuse2:
```bash
# Ubuntu 22.04+
sudo apt-get install libfuse2
```

### Missing dependencies
If you encounter missing library errors, you may need to install additional system dependencies. Check the error message and install the required packages.

## Notes

- The AppImage includes all Python dependencies, so it's a standalone executable
- The example config file (`config.yaml.example`) is included in the AppImage
- Users will need to create their own `config.yaml` file in their home directory or current directory
- The AppImage is built for x86_64 architecture only
