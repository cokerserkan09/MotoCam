from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')

# Android 14+ tek-uygulama seciminde secilen uygulama one gecebilir. Bu sirada
# MotoCam arka plana dusup mediaProjection foreground service baslatmasi Android 15'te
# engellenebilir. MotoCam yalnizca oynatma sesini yakaladigi icin projeksiyon onayini
# varsayilan ekran oturumu olarak iste; kullanici YouTube'u ayri secmek zorunda kalmasin.
old = '''            val mgr = getSystemService(android.content.Context.MEDIA_PROJECTION_SERVICE) as android.media.projection.MediaProjectionManager
            startActivityForResult(mgr.createScreenCaptureIntent(), mediaProjectionRequestCode)
'''
new = '''            val mgr = getSystemService(android.content.Context.MEDIA_PROJECTION_SERVICE) as android.media.projection.MediaProjectionManager
            val captureIntent = if (android.os.Build.VERSION.SDK_INT >= 34) {
                mgr.createScreenCaptureIntent(android.media.projection.MediaProjectionConfig.createConfigForDefaultDisplay())
            } else {
                mgr.createScreenCaptureIntent()
            }
            startActivityForResult(captureIntent, mediaProjectionRequestCode)
'''
if old not in s:
    raise SystemExit('v4.1 requestPlaybackCapturePermission anchor bulunamadi')
s = s.replace(old, new, 1)

# Izin sonucu geldiginde Activity tekrar RESUMED olmadan FGS baslatma yarisi olmasin.
# Sonucu sakla; baslatmayi ana pencere yeniden odaga geldikten hemen sonra yap.
old_result = '''                if (pendingStartAfterProjectionConsent) {
                    pendingStartAfterProjectionConsent = false
                    if (startPlaybackCaptureIfNeeded()) {
'''
new_result = '''                if (pendingStartAfterProjectionConsent) {
                    pendingStartAfterProjectionConsent = false
                    binding.root.post {
                    if (startPlaybackCaptureIfNeeded()) {
'''
if old_result not in s:
    raise SystemExit('v4.1 consent start anchor bulunamadi')
s = s.replace(old_result, new_result, 1)

# v4.1 blogundaki if kapanisindan sonra post blogunu da kapat.
needle = '''                    }
                } else {
                    toast("Medya sesi yakalama izni verildi.")
'''
repl = '''                    }
                    }
                } else {
                    toast("Medya sesi yakalama izni verildi.")
'''
if needle not in s:
    raise SystemExit('v4.1 consent closing anchor bulunamadi')
s = s.replace(needle, repl, 1)

kt.write_text(s, encoding='utf-8')

g = Path('motocam/app/build.gradle.kts')
t = g.read_text(encoding='utf-8')
t = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 32', t, count=1)
t = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "4.2.0"', t, count=1)
g.write_text(t, encoding='utf-8')
print('MotoCam v4.2: full-display MediaProjection consent + foreground-safe service start')
