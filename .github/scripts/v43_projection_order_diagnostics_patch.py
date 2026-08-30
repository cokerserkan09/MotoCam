from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')
svc=Path('motocam/app/src/main/java/com/motocam/app/PlaybackCaptureService.kt')
p=svc.read_text(encoding='utf-8')

# Android resmi akis: consent sonucu gelir gelmez Activity foreground durumundayken FGS'yi baslat.
# v4.2'de eklenen binding.root.post gecikmesini kaldir.
s=s.replace('''                if (pendingStartAfterProjectionConsent) {
                    pendingStartAfterProjectionConsent = false
                    binding.root.post {
                    if (startPlaybackCaptureIfNeeded()) {
''','''                if (pendingStartAfterProjectionConsent) {
                    pendingStartAfterProjectionConsent = false
                    if (startPlaybackCaptureIfNeeded()) {
''',1)
s=s.replace('''                    }
                    }
                } else {
                    toast("Medya sesi yakalama izni verildi.")
''','''                    }
                } else {
                    toast("Medya sesi yakalama izni verildi.")
''',1)

# Uygulama cokerse sonraki acilista tam nedeni ekranda goster: artik tahmin yok.
anchor='''        super.onCreate(savedInstanceState)
'''
if anchor in s and 'motocam_crash' not in s:
    repl='''        super.onCreate(savedInstanceState)
        val crashPrefs = getSharedPreferences("motocam_crash", MODE_PRIVATE)
        val previousHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, error ->
            try {
                val trace = android.util.Log.getStackTraceString(error)
                crashPrefs.edit().putString("last_crash", trace.take(12000)).apply()
            } catch (_: Throwable) {}
            previousHandler?.uncaughtException(thread, error)
        }
        crashPrefs.getString("last_crash", null)?.let { report ->
            crashPrefs.edit().remove("last_crash").apply()
            android.app.AlertDialog.Builder(this)
                .setTitle("MotoCam hata raporu")
                .setMessage(report.take(5000))
                .setPositiveButton("Tamam", null)
                .show()
        }
'''
    s=s.replace(anchor,repl,1)

# Servis hatalarini process olse bile kalici kaydet.
p=p.replace('''        } catch (t: Throwable) {
            lastError = t.javaClass.simpleName + ": " + (t.message ?: "medya sesi baslatma hatasi")
''','''        } catch (t: Throwable) {
            lastError = t.javaClass.simpleName + ": " + (t.message ?: "medya sesi baslatma hatasi")
            try { getSharedPreferences("motocam_crash", MODE_PRIVATE).edit().putString("last_crash", android.util.Log.getStackTraceString(t).take(12000)).apply() } catch (_: Throwable) {}
''',1)
p=p.replace('''            } catch (t: Throwable) {
                lastError = t.javaClass.simpleName + ": " + (t.message ?: "AudioPlaybackCapture hatasi")
''','''            } catch (t: Throwable) {
                lastError = t.javaClass.simpleName + ": " + (t.message ?: "AudioPlaybackCapture hatasi")
                try { getSharedPreferences("motocam_crash", MODE_PRIVATE).edit().putString("last_crash", android.util.Log.getStackTraceString(t).take(12000)).apply() } catch (_: Throwable) {}
''',1)

# Playback-only modunda foreground type kesinlikle sadece mediaProjection olsun.
# mixed icin mikrofon tipi ancak RECORD_AUDIO gercekten verilmis ise eklenir.
old='''            var t = ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            if (currentMode == "mixed") t = t or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            t
'''
new='''            var t = ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            if (currentMode == "mixed" && androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                t = t or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            }
            t
'''
if old in p: p=p.replace(old,new,1)

kt.write_text(s,encoding='utf-8')
svc.write_text(p,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 33',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.3.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v4.3: official MediaProjection order + persistent crash diagnostics')
