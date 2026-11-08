#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${ANDROID_HOME:?Set ANDROID_HOME to Android SDK path}"
bt="$ANDROID_HOME/build-tools/35.0.0"
platform="$ANDROID_HOME/platforms/android-35/android.jar"
mkdir -p build/generated build/classes build/dex ../../artifacts
python3 - <<'GEN'
import xml.etree.ElementTree as ET
ns='http://schemas.android.com/apk/res/android'
ET.register_namespace('android',ns)
tree=ET.parse('app/src/main/AndroidManifest.xml')
r=tree.getroot();r.set('package','cn.roomguard');r.set('{'+ns+'}versionCode','3');r.set('{'+ns+'}versionName','2.0')
tree.write('build/AndroidManifest.xml',encoding='utf-8',xml_declaration=True)
GEN
"$bt/aapt" package -f -m -J build/generated -M build/AndroidManifest.xml -S app/src/main/res -I "$platform" -F build/base.apk
find app/src/main/java build/generated -name '*.java' > build/sources.txt
javac --release 8 -encoding UTF-8 -classpath "$platform" -d build/classes @build/sources.txt
jar cf build/classes.jar -C build/classes .
"$bt/d8" --min-api 22 --lib "$platform" --output build/dex build/classes.jar
cp build/base.apk build/unsigned.apk
(cd build/dex && "$bt/aapt" add ../unsigned.apk classes.dex)
"$bt/zipalign" -f 4 build/unsigned.apk build/aligned.apk
# Development/test signature only. Use your own protected release key for distribution.
if [ ! -f build/development.jks ]; then
 keytool -genkeypair -keystore build/development.jks -storepass android -keypass android -alias roomguard -keyalg RSA -keysize 2048 -validity 3650 -dname 'CN=RoomGuard Development,O=Competition'
fi
"$bt/apksigner" sign --ks build/development.jks --ks-key-alias roomguard --ks-pass pass:android --key-pass pass:android --out ../../artifacts/RoomGuard-Android5.1.apk build/aligned.apk
"$bt/apksigner" verify --verbose ../../artifacts/RoomGuard-Android5.1.apk
"$bt/aapt" dump badging ../../artifacts/RoomGuard-Android5.1.apk | head -8
