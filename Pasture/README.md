# Pasture — offline Android app

This is a native Android WebView wrapper around a self-contained local version of Pasture. All images and sound files are packaged in `app/src/main/assets`; the app requests no internet permission and does not contact a server.

## Build the APK on Windows

1. Install Android Studio (with Android SDK Platform 35 and a JDK; Android Studio's bundled JBR is fine).
2. Open this `pasture-android` folder in Android Studio.
3. Allow Gradle sync to finish. The first build needs internet to download the Android Gradle Plugin and SDK components; the installed app itself works fully offline.
4. Choose **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
5. Android Studio writes the APK to `app/build/outputs/apk/debug/app-debug.apk`.
6. Transfer that APK to your Galaxy S24 Ultra and install it. If Android asks, allow your file manager/browser to install unknown apps.

Package: `com.example.pasture` · Min Android: 6.0 (API 23) · Target: API 35

No `INTERNET` permission is declared. The web content, photos, and audio are all local assets.
