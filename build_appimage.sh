#!/bin/bash
# Build script for creating ES-CLI AppImage for x86_64 Linux

set -e  # Exit on error (disabled for extraction step)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
APPIMAGE_DIR="${BUILD_DIR}/ES-CLI.AppDir"
APPIMAGE_NAME="ES-CLI-x86_64.AppImage"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building ES-CLI AppImage...${NC}"

# Clean previous build
if [ -d "${BUILD_DIR}" ]; then
    echo -e "${YELLOW}Cleaning previous build...${NC}"
    rm -rf "${BUILD_DIR}"
fi

mkdir -p "${APPIMAGE_DIR}"

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}python3 is required but not installed.${NC}" >&2; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo -e "${RED}pip3 is required but not installed.${NC}" >&2; exit 1; }
command -v wget >/dev/null 2>&1 || { echo -e "${RED}wget is required but not installed.${NC}" >&2; exit 1; }

# Check for extraction tools (at least one is needed)
HAS_UNSQUASHFS=$(command -v unsquashfs >/dev/null 2>&1 && echo "yes" || echo "no")
HAS_FUSE="no"
if ldconfig -p 2>/dev/null | grep -q libfuse.so.2 || [ -f /usr/lib/x86_64-linux-gnu/libfuse.so.2 ] || [ -f /lib/x86_64-linux-gnu/libfuse.so.2 ]; then
    HAS_FUSE="yes"
fi

if [ "$HAS_UNSQUASHFS" = "no" ] && [ "$HAS_FUSE" = "no" ]; then
    echo -e "${YELLOW}Warning: Neither unsquashfs nor libfuse2 found.${NC}"
    echo -e "${YELLOW}Install one of:${NC}"
    echo -e "${YELLOW}  - sudo apt-get install squashfs-tools (recommended)${NC}"
    echo -e "${YELLOW}  - sudo apt-get install libfuse2${NC}"
    echo -e "${YELLOW}The script will try to proceed anyway...${NC}"
fi

# Create virtual environment
echo -e "${GREEN}Creating virtual environment...${NC}"
VENV_DIR="${BUILD_DIR}/venv"
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install build dependencies
echo -e "${GREEN}Installing build dependencies...${NC}"
pip install pyinstaller

# Install application dependencies
echo -e "${GREEN}Installing application dependencies...${NC}"
pip install -r "${SCRIPT_DIR}/requirements.txt"

# Build with PyInstaller
echo -e "${GREEN}Building executable with PyInstaller...${NC}"
pyinstaller \
    --name ES-CLI \
    --onefile \
    --console \
    --clean \
    --distpath "${APPIMAGE_DIR}/usr/bin" \
    --workpath "${BUILD_DIR}/pyinstaller" \
    --specpath "${BUILD_DIR}/pyinstaller" \
    --add-data "${SCRIPT_DIR}/config.yaml.example:." \
    --hidden-import urwid \
    --hidden-import urwid.display \
    --hidden-import urwid.display.common \
    --hidden-import urwid.display.lcd \
    --hidden-import urwid.display.raw \
    --hidden-import urwid.display.screen \
    --hidden-import urwid.display.escape \
    --hidden-import urwid.widget \
    --hidden-import urwid.widget.wimp \
    --hidden-import urwid.compat \
    --hidden-import urwid.event_loop \
    --hidden-import urwid.event_loop.select_loop \
    --hidden-import urwid.event_loop.main_loop \
    --hidden-import urwid.signals \
    --hidden-import urwid.util \
    --hidden-import urwid.raw_display \
    --hidden-import urwid.curses_display \
    --hidden-import yaml \
    --hidden-import elasticsearch \
    --hidden-import elasticsearch._sync \
    --hidden-import elasticsearch._sync.client \
    --hidden-import requests \
    --hidden-import requests.auth \
    --hidden-import urllib3 \
    --hidden-import urllib3.util \
    --hidden-import urllib3.poolmanager \
    --hidden-import urllib3.exceptions \
    --hidden-import certifi \
    --hidden-import charset_normalizer \
    --collect-all urwid \
    --collect-all elasticsearch \
    "${SCRIPT_DIR}/main.py"

# Create AppDir structure
echo -e "${GREEN}Creating AppDir structure...${NC}"

# Copy AppRun
cat > "${APPIMAGE_DIR}/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/usr/bin/ES-CLI" "$@"
EOF
chmod +x "${APPIMAGE_DIR}/AppRun"

# Create .desktop file
cat > "${APPIMAGE_DIR}/ES-CLI.desktop" << 'EOF'
[Desktop Entry]
Name=ES-CLI
Comment=Elasticsearch CLI Tool
Exec=ES-CLI
Icon=ES-CLI
Type=Application
Categories=Utility;
Terminal=true
EOF

# Create a simple placeholder icon if one doesn't exist
# Check if user provided an icon
if [ -f "${SCRIPT_DIR}/icon.png" ]; then
    cp "${SCRIPT_DIR}/icon.png" "${APPIMAGE_DIR}/ES-CLI.png"
    echo -e "${GREEN}Using provided icon${NC}"
elif [ -f "${SCRIPT_DIR}/icon.svg" ]; then
    cp "${SCRIPT_DIR}/icon.svg" "${APPIMAGE_DIR}/ES-CLI.svg"
    echo -e "${GREEN}Using provided SVG icon${NC}"
else
    # Create a simple 256x256 placeholder PNG using ImageMagick if available, otherwise skip
    if command -v convert >/dev/null 2>&1; then
        echo -e "${GREEN}Creating placeholder icon...${NC}"
        convert -size 256x256 xc:transparent \
            -fill '#4A90E2' -draw 'circle 128,128 128,64' \
            -fill white -font Arial-Bold -pointsize 72 -gravity center \
            -annotate +0+0 'ES' \
            "${APPIMAGE_DIR}/ES-CLI.png" 2>/dev/null || {
            echo -e "${YELLOW}Icon creation failed, continuing without icon${NC}"
            # Remove Icon line from desktop file
            sed -i '/^Icon=/d' "${APPIMAGE_DIR}/ES-CLI.desktop"
        }
    else
        echo -e "${YELLOW}No icon found and ImageMagick not available. Creating desktop file without icon...${NC}"
        # Remove Icon line from desktop file
        sed -i '/^Icon=/d' "${APPIMAGE_DIR}/ES-CLI.desktop"
    fi
fi

# Copy example config to AppDir
mkdir -p "${APPIMAGE_DIR}/usr/share/ES-CLI"
cp "${SCRIPT_DIR}/config.yaml.example" "${APPIMAGE_DIR}/usr/share/ES-CLI/"

# Download and extract appimagetool if not present
APPIMAGETOOL_DIR="${BUILD_DIR}/appimagetool"
APPIMAGETOOL="${APPIMAGETOOL_DIR}/appimagetool"
APPIMAGETOOL_APPIMAGE="${BUILD_DIR}/appimagetool-x86_64.AppImage"

if [ ! -f "${APPIMAGETOOL}" ]; then
    # Download appimagetool AppImage if not present
    if [ ! -f "${APPIMAGETOOL_APPIMAGE}" ]; then
        echo -e "${GREEN}Downloading appimagetool...${NC}"
        wget -q -O "${APPIMAGETOOL_APPIMAGE}" \
            "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" || {
            echo -e "${RED}Failed to download appimagetool.${NC}"
            echo -e "${YELLOW}Please download it manually from:${NC}"
            echo "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
            exit 1
        }
        chmod +x "${APPIMAGETOOL_APPIMAGE}"
    fi
    
    # Extract appimagetool to avoid FUSE requirement during build
    echo -e "${GREEN}Extracting appimagetool...${NC}"
    mkdir -p "${APPIMAGETOOL_DIR}"
    cd "${APPIMAGETOOL_DIR}"
    
    EXTRACT_SUCCESS=0
    
    # Method 1: Try using unsquashfs (doesn't require FUSE)
    if command -v unsquashfs >/dev/null 2>&1; then
        echo -e "${GREEN}Using unsquashfs to extract...${NC}"
        if unsquashfs -f -d squashfs-root "${APPIMAGETOOL_APPIMAGE}" > /dev/null 2>&1; then
            EXTRACT_SUCCESS=1
        fi
    fi
    
    # Method 2: Try appimage-extract (might require FUSE)
    if [ $EXTRACT_SUCCESS -eq 0 ]; then
        echo -e "${GREEN}Trying appimage-extract...${NC}"
        set +e
        "${APPIMAGETOOL_APPIMAGE}" --appimage-extract > /dev/null 2>&1
        EXTRACT_STATUS=$?
        set -e
        if [ $EXTRACT_STATUS -eq 0 ]; then
            EXTRACT_SUCCESS=1
        fi
    fi
    
    if [ $EXTRACT_SUCCESS -eq 1 ] && [ -f "${APPIMAGETOOL_DIR}/squashfs-root/AppRun" ]; then
        APPIMAGETOOL="${APPIMAGETOOL_DIR}/squashfs-root/AppRun"
        echo -e "${GREEN}Successfully extracted appimagetool${NC}"
    else
        # If extraction fails, we need FUSE - provide helpful error
        echo -e "${RED}Failed to extract appimagetool.${NC}"
        echo -e "${YELLOW}This requires libfuse2.${NC}"
        echo -e "${YELLOW}Please install it with: sudo apt-get install libfuse2${NC}"
        echo -e "${YELLOW}Or install squashfs-tools: sudo apt-get install squashfs-tools${NC}"
        echo -e "${YELLOW}Then run this script again.${NC}"
        cd "${SCRIPT_DIR}"
        exit 1
    fi
    cd "${SCRIPT_DIR}"
fi

# Create AppImage
echo -e "${GREEN}Creating AppImage...${NC}"
set +e  # Temporarily disable exit on error to capture the actual error
ARCH=x86_64 "${APPIMAGETOOL}" "${APPIMAGE_DIR}" "${BUILD_DIR}/${APPIMAGE_NAME}" 2>&1 | tee "${BUILD_DIR}/appimagetool.log"
APPIMAGE_STATUS=$?
set -e

if [ $APPIMAGE_STATUS -ne 0 ]; then
    echo -e "${RED}Failed to create AppImage.${NC}"
    
    # Check if it's an icon issue
    if grep -q "defined in desktop file but not found" "${BUILD_DIR}/appimagetool.log" 2>/dev/null; then
        echo -e "${YELLOW}Icon issue detected. Removing icon reference and retrying...${NC}"
        sed -i '/^Icon=/d' "${APPIMAGE_DIR}/ES-CLI.desktop"
        ARCH=x86_64 "${APPIMAGETOOL}" "${APPIMAGE_DIR}" "${BUILD_DIR}/${APPIMAGE_NAME}" || {
            echo -e "${RED}Still failed after removing icon reference.${NC}"
            exit 1
        }
    else
        echo -e "${YELLOW}Troubleshooting:${NC}"
        echo "1. Check the log: ${BUILD_DIR}/appimagetool.log"
        echo "2. Make sure libfuse2 is installed: sudo apt-get install libfuse2"
        exit 1
    fi
fi

# Make AppImage executable
chmod +x "${BUILD_DIR}/${APPIMAGE_NAME}"

echo -e "${GREEN}✓ Build complete!${NC}"
echo -e "${GREEN}AppImage location: ${BUILD_DIR}/${APPIMAGE_NAME}${NC}"

# Cleanup (optional - comment out to keep for debugging)
deactivate
rm -rf "${VENV_DIR}"
rm -rf "${BUILD_DIR}/pyinstaller"
# Keep appimagetool extracted for faster rebuilds
# rm -rf "${APPIMAGETOOL_DIR}"

echo -e "${GREEN}Done!${NC}"
echo -e "${GREEN}AppImage location: ${BUILD_DIR}/${APPIMAGE_NAME}${NC}"
