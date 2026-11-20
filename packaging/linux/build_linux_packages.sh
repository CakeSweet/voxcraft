#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

DEFAULT_VER="$(python3 - <<'PY'
import re
with open("app.py", "r", encoding="utf-8") as f:
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
print(m.group(1) if m else "2.1.0")
PY
)"

VERSION="${1:-$DEFAULT_VER}"
VERSION="${VERSION#v}"
ARCH_DEB="amd64"
ARCH_RPM="x86_64"
PKG_NAME="voxcraft-studio"
OUTPUT_DIR="$ROOT_DIR/Output"
WORK_DIR="$ROOT_DIR/build/linux_pkg"

mkdir -p "$OUTPUT_DIR" "$WORK_DIR"
rm -rf "$ROOT_DIR/dist/VoxCraftStudio" "$WORK_DIR/deb_root" "$WORK_DIR/rpmbuild"

echo "[1/3] Building Linux binary with PyInstaller (v$VERSION)..."
python3 -m PyInstaller --noconfirm --clean --windowed \
  --name "VoxCraftStudio" \
  --add-data "assets:assets" \
  --hidden-import=pystray._xorg \
  --hidden-import=pystray._appindicator \
  --hidden-import=PIL._tkinter_finder \
  --collect-all customtkinter \
  app.py

stage_payload() {
  local dest_root="$1"
  mkdir -p \
    "$dest_root/opt/voxcraft-studio" \
    "$dest_root/usr/bin" \
    "$dest_root/usr/share/applications" \
    "$dest_root/usr/share/icons/hicolor/256x256/apps"

  cp -a "$ROOT_DIR/dist/VoxCraftStudio/." "$dest_root/opt/voxcraft-studio/"
  chmod 0755 "$dest_root/opt/voxcraft-studio/VoxCraftStudio"

  cat > "$dest_root/usr/bin/voxcraft-studio" <<'EOF'
#!/usr/bin/env sh
exec /opt/voxcraft-studio/VoxCraftStudio "$@"
EOF
  chmod 0755 "$dest_root/usr/bin/voxcraft-studio"

  cat > "$dest_root/usr/share/applications/voxcraft-studio.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=VoxCraft Studio
GenericName=Real-Time Voice Modulator
Comment=Real-Time Voice Modulator and DSP Audio Effects Studio
Exec=/usr/bin/voxcraft-studio %U
Icon=voxcraft-studio
Terminal=false
Categories=AudioVideo;Audio;
Keywords=voice;modulator;dsp;audio;microphone;
StartupWMClass=VoxCraftStudio
EOF
  chmod 0644 "$dest_root/usr/share/applications/voxcraft-studio.desktop"

  if [ -f "$ROOT_DIR/assets/voxcraft.png" ]; then
    install -m 0644 "$ROOT_DIR/assets/voxcraft.png" "$dest_root/usr/share/icons/hicolor/256x256/apps/voxcraft-studio.png"
  fi
}

echo "[2/3] Building .deb package..."
if command -v dpkg-deb >/dev/null 2>&1; then
  DEB_ROOT="$WORK_DIR/deb_root"
  stage_payload "$DEB_ROOT"
  mkdir -p "$DEB_ROOT/DEBIAN"

  INSTALLED_KB="$(du -sk "$DEB_ROOT/opt" "$DEB_ROOT/usr" | awk '{s+=$1} END{print s+0}')"
  cat > "$DEB_ROOT/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: sound
Priority: optional
Architecture: $ARCH_DEB
Installed-Size: $INSTALLED_KB
Depends: libportaudio2, libc6, libx11-6
Recommends: gir1.2-ayatanaappindicator3-0.1 | gir1.2-appindicator3-0.1, python3-gi
Maintainer: CakeSweet <noreply@github.com>
Homepage: https://github.com/CakeSweet/voxcraft
Description: Real-time desktop voice modulator and DSP studio
 VoxCraft Studio is a native real-time voice modulator with Noise Gate,
 Compressor, Pitch/Frequency Shifter, Vocoder, 5-Band EQ, Modulation,
 Distortion, Echo and Reverb effects.
EOF

  cat > "$DEB_ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF
  chmod 0755 "$DEB_ROOT/DEBIAN/postinst"

  DEB_OUT="$OUTPUT_DIR/${PKG_NAME}_${VERSION}_${ARCH_DEB}.deb"
  dpkg-deb --build --root-owner-group "$DEB_ROOT" "$DEB_OUT"
  echo "Created: $DEB_OUT"
else
  echo "[WARN] dpkg-deb not found; skipping .deb package."
fi

echo "[3/3] Building .rpm package..."
if command -v rpmbuild >/dev/null 2>&1; then
  RPM_TOP="$WORK_DIR/rpmbuild"
  mkdir -p "$RPM_TOP"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
  RPM_SRC="$WORK_DIR/rpm_stage"
  rm -rf "$RPM_SRC"
  stage_payload "$RPM_SRC"

  SPEC_FILE="$RPM_TOP/SPECS/${PKG_NAME}.spec"
  cat > "$SPEC_FILE" <<EOF
%global _build_id_links none
%global debug_package %{nil}
AutoReqProv: no

Name:           $PKG_NAME
Version:        $VERSION
Release:        1
Summary:        Real-time desktop voice modulator and DSP studio
License:        MIT
URL:            https://github.com/CakeSweet/voxcraft
Requires:       portaudio

%description
VoxCraft Studio is a native real-time voice modulator with Noise Gate,
Compressor, Pitch/Frequency Shifter, Vocoder, 5-Band EQ, Modulation,
Distortion, Echo and Reverb effects.

%install
mkdir -p %{buildroot}
cp -a "$RPM_SRC"/* %{buildroot}/

%post
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

%files
/opt/voxcraft-studio
/usr/bin/voxcraft-studio
/usr/share/applications/voxcraft-studio.desktop
/usr/share/icons/hicolor/256x256/apps/voxcraft-studio.png
EOF

  rpmbuild -bb \
    --define "_topdir $RPM_TOP" \
    --target "$ARCH_RPM" \
    "$SPEC_FILE"

  BUILT_RPM="$(find "$RPM_TOP/RPMS" -name '*.rpm' | head -n 1)"
  if [ -n "$BUILT_RPM" ]; then
    RPM_OUT="$OUTPUT_DIR/${PKG_NAME}-${VERSION}-1.${ARCH_RPM}.rpm"
    cp -f "$BUILT_RPM" "$RPM_OUT"
    echo "Created: $RPM_OUT"
  fi
else
  echo "[WARN] rpmbuild not found; skipping .rpm package."
fi
