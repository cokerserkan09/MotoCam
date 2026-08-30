from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')

# Android 14/15 icin medya yakalama iznini Ayarlar'da onceden almayi birak.
# Her yeni normal kayit baslangicinda taze MediaProjection onayi istenecek.
s = s.replace('''                    val chosenAudio = videoAudioSource()\n                    if ((chosenAudio == "playback" || chosenAudio == "mixed") && !playbackCaptureReady()) requestPlaybackCapturePermission()\n''', '''                    val chosenAudio = videoAudioSource()\n                    if (chosenAudio == "playback" || chosenAudio == "mixed") {\n                        binding.tvVoice.text = "Medya sesi seçildi • kayıt başlarken Android izni istenecek"\n                    }\n''', 1)

# State: izin sonucu geldiginde kaydi otomatik devam ettir.
anchor = '    private val mediaProjectionRequestCode = 7341\n'
if anchor not in s:
    raise SystemExit('mediaProjectionRequestCode bulunamadi')
if 'pendingStartAfterProjectionConsent' not in s:
    s = s.replace(anchor, anchor + '    private var pendingStartAfterProjectionConsent = false\n', 1)

# Izin fonksiyonunu tekrar tekrar acilmaya karsi koru.
old_req = '''    private fun requestPlaybackCapturePermission() {\n        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.Q) {\n            toast("Telefon sesi kaydı Android 10 veya üzeri gerektirir.")\n            return\n        }\n        val mgr = getSystemService(android.content.Context.MEDIA_PROJECTION_SERVICE) as android.media.projection.MediaProjectionManager\n        startActivityForResult(mgr.createScreenCaptureIntent(), mediaProjectionRequestCode)\n    }\n'''
new_req = '''    private fun requestPlaybackCapturePermission() {\n        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.Q) {\n            toast("Telefon sesi kaydı Android 10 veya üzeri gerektirir.")\n            pendingStartAfterProjectionConsent = false\n            return\n        }\n        try {\n            val mgr = getSystemService(android.content.Context.MEDIA_PROJECTION_SERVICE) as android.media.projection.MediaProjectionManager\n            startActivityForResult(mgr.createScreenCaptureIntent(), mediaProjectionRequestCode)\n        } catch (t: Throwable) {\n            pendingStartAfterProjectionConsent = false\n            binding.tvVoice.text = "Medya izni açılamadı: ${t.javaClass.simpleName}"\n            toast("Android medya yakalama izni açılamadı.")\n        }\n    }\n'''
if old_req not in s:
    raise SystemExit('requestPlaybackCapturePermission blogu bulunamadi')
s = s.replace(old_req, new_req, 1)

# onActivityResult: onay gelir gelmez servisi baslat ve hazir olunca kaydi devam ettir.
old_result = '''        if (requestCode == mediaProjectionRequestCode) {\n            if (resultCode == android.app.Activity.RESULT_OK && data != null) {\n                pendingMediaProjectionIntent = data\n                pendingMediaProjectionResultCode = resultCode\n                binding.tvVoice.text = "Telefon / medya sesi yakalama izni hazır"\n                toast("Medya sesi yakalama izni verildi.")\n            } else {\n                pendingMediaProjectionIntent = null\n                toast("Medya sesi yakalama izni verilmedi.")\n            }\n        }\n'''
new_result = '''        if (requestCode == mediaProjectionRequestCode) {\n            if (resultCode == android.app.Activity.RESULT_OK && data != null) {\n                pendingMediaProjectionIntent = data\n                pendingMediaProjectionResultCode = resultCode\n                binding.tvVoice.text = "Medya sesi izni verildi • hazırlanıyor…"\n                if (pendingStartAfterProjectionConsent) {\n                    pendingStartAfterProjectionConsent = false\n                    if (startPlaybackCaptureIfNeeded()) {\n                        binding.root.postDelayed({\n                            when {\n                                PlaybackCaptureService.captureReady -> {\n                                    pendingMediaProjectionIntent = null\n                                    startRecording()\n                                }\n                                PlaybackCaptureService.lastError != null -> {\n                                    pendingMediaProjectionIntent = null\n                                    val msg = PlaybackCaptureService.lastError ?: "bilinmeyen hata"\n                                    binding.tvVoice.text = "Medya sesi başlatılamadı: $msg"\n                                    toast("Medya sesi başlatılamadı.")\n                                }\n                                else -> {\n                                    binding.root.postDelayed({\n                                        if (PlaybackCaptureService.captureReady) {\n                                            pendingMediaProjectionIntent = null\n                                            startRecording()\n                                        } else {\n                                            val msg = PlaybackCaptureService.lastError ?: "telefon medya yakalamayı başlatmadı"\n                                            binding.tvVoice.text = "Medya sesi başlatılamadı: $msg"\n                                            toast("Medya sesi hazır değil; kayıt başlatılmadı.")\n                                        }\n                                    }, 1200)\n                                }\n                            }\n                        }, 500)\n                    }\n                } else {\n                    toast("Medya sesi yakalama izni verildi.")\n                }\n            } else {\n                pendingStartAfterProjectionConsent = false\n                pendingMediaProjectionIntent = null\n                binding.tvVoice.text = "Medya sesi izni verilmedi"\n                toast("Medya sesi yakalama izni verilmedi.")\n            }\n        }\n'''
if old_result not in s:
    raise SystemExit('onActivityResult medya blogu bulunamadi')
s = s.replace(old_result, new_result, 1)

# v4.0 start gate'i Android 14/15 uyumlu taze izin akisi ile degistir.
pattern = re.compile(r'''    private fun startRecording\(\) \{\n        val realPlaybackMode = videoAudioSource\(\)\n        if \(realPlaybackMode == "playback" \|\| realPlaybackMode == "mixed"\) \{\n            if \(!PlaybackCaptureService\.captureReady\) \{\n                if \(!playbackCaptureReady\(\)\) \{\n                    toast\("Telefon / medya sesi için Android yakalama izni gerekli\."\)\n                    requestPlaybackCapturePermission\(\)\n                    return\n                \}\n                if \(!startPlaybackCaptureIfNeeded\(\)\) return\n                binding\.tvVoice\.text = "Medya sesi hazırlanıyor…"\n                binding\.root\.postDelayed\(\{.*?\n                \}, 500\)\n                return\n            \}\n        \}\n''', re.S)
match = pattern.search(s)
if not match:
    raise SystemExit('v4.0 start gate bulunamadi')
new_gate = '''    private fun startRecording() {\n        val realPlaybackMode = videoAudioSource()\n        if (realPlaybackMode == "playback" || realPlaybackMode == "mixed") {\n            if (!PlaybackCaptureService.captureReady) {\n                if (PlaybackCaptureService.projectionAlive) {\n                    if (!startPlaybackCaptureIfNeeded()) return\n                    binding.tvVoice.text = "Medya sesi hazırlanıyor…"\n                    binding.root.postDelayed({\n                        if (PlaybackCaptureService.captureReady) startRecording()\n                        else {\n                            val msg = PlaybackCaptureService.lastError ?: "medya sesi hazırlanamadı"\n                            binding.tvVoice.text = "Medya sesi başlatılamadı: $msg"\n                            toast("Medya sesi hazır değil; kayıt başlatılmadı.")\n                        }\n                    }, 700)\n                    return\n                }\n                // Android 14/15: her yeni MediaProjection oturumu icin taze kullanici onayi al.\n                pendingMediaProjectionIntent = null\n                pendingMediaProjectionResultCode = android.app.Activity.RESULT_CANCELED\n                pendingStartAfterProjectionConsent = true\n                binding.tvVoice.text = "Medya sesi için Android izni bekleniyor…"\n                requestPlaybackCapturePermission()\n                return\n            }\n        }\n'''
s = s[:match.start()] + new_gate + s[match.end():]

# Activity kapanirken bekleyen baslatma durumunu temizle.
destroy = '    override fun onDestroy() {\n'
if destroy in s and 'pendingStartAfterProjectionConsent = false' not in s[s.find(destroy):s.find(destroy)+220]:
    s = s.replace(destroy, destroy + '        pendingStartAfterProjectionConsent = false\n', 1)

kt.write_text(s, encoding='utf-8')

g = Path('motocam/app/build.gradle.kts')
t = g.read_text(encoding='utf-8')
t = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 31', t, count=1)
t = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "4.1.0"', t, count=1)
g.write_text(t, encoding='utf-8')

print('MotoCam v4.1: Android 14/15 fresh MediaProjection consent + auto resume')
