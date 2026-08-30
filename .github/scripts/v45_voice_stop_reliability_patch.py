from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')

# Non-crash logic failures must also be visible to the user.
anchor = '    private fun handleLiveVoskPartial(hypothesis: String?) {\n'
if anchor not in s:
    raise SystemExit('handleLiveVoskPartial bulunamadi')

helpers = r'''    private fun reportMotoCamLogicIssue(message: String) {
        val report = "MotoCam çalışma raporu\n" +
            "Sürüm: 4.5.0\n" +
            "Android: ${android.os.Build.VERSION.SDK_INT}\n" +
            "Durum: ${binding.tvStatus.text}\n" +
            "Ses: ${binding.tvVoice.text}\n\n" + message
        try {
            getSharedPreferences("motocam_crash", MODE_PRIVATE)
                .edit().putString("last_crash", report.take(12000)).apply()
        } catch (_: Throwable) {}
        try {
            if (!isFinishing && !isDestroyed) {
                android.app.AlertDialog.Builder(this)
                    .setTitle("MotoCam hata raporu")
                    .setMessage(report.take(5000))
                    .setPositiveButton("Tamam", null)
                    .show()
            }
        } catch (_: Throwable) {}
    }

    private fun requestVoiceStop(source: String) {
        runOnUiThread {
            val stopWord = stopCommand()
            val before = activeRecording
            binding.tvVoice.text = "Komut alındı: ${stopWord.uppercase()} • durduruluyor"
            if (before == null) {
                reportMotoCamLogicIssue("Durdurma kelimesi algılandı ($source) fakat activeRecording null. Kayıt durumu ile CameraX nesnesi uyuşmuyor.")
                return@runOnUiThread
            }
            voiceStopRequested = true
            try {
                stopRecording()
            } catch (t: Throwable) {
                reportMotoCamLogicIssue("stopRecording() hata verdi ($source): ${t.javaClass.name}: ${t.message}\n${android.util.Log.getStackTraceString(t)}")
                return@runOnUiThread
            }

            binding.root.postDelayed({
                if (activeRecording === before) {
                    try {
                        binding.tvVoice.text = "Durdurma komutu tekrar uygulanıyor…"
                        before.stop()
                    } catch (t: Throwable) {
                        reportMotoCamLogicIssue("Sesli durdurma fallback hata verdi ($source): ${t.javaClass.name}: ${t.message}\n${android.util.Log.getStackTraceString(t)}")
                        return@postDelayed
                    }
                    binding.root.postDelayed({
                        if (activeRecording === before) {
                            reportMotoCamLogicIssue("Durdurma kelimesi algılandı ($source), stopRecording ve doğrudan Recording.stop() çağrıldı; ancak 4 saniye sonra kayıt nesnesi hâlâ aktif görünüyor.")
                        }
                    }, 1500L)
                }
            }, 2500L)
        }
    }

'''
if 'private fun requestVoiceStop(' not in s:
    s = s.replace(anchor, helpers + anchor, 1)

# Generated Kotlin must contain Regex("\\s+"). Use a raw Python replacement so the
# Kotlin compiler receives a valid escaped backslash, not Regex("\s+").
s = s.replace('val words = clean.split(Regex("\\\\s+")).filter { it.isNotBlank() }',
              r'val words = clean.split(Regex("\\s+")).filter { it.isNotBlank() }', 1)

old_partial = '''                last == stopWord -> {
                    lastVoiceCommandMs = now
                    runOnUiThread {
                        binding.tvVoice.text = "Duyuldu: $stopWord"
                        voiceStopRequested = true
                        stopRecording()
                    }
                }
'''
new_partial = '''                last == stopWord -> {
                    lastVoiceCommandMs = now
                    binding.tvVoice.text = "Duyuldu: $stopWord"
                    requestVoiceStop("Vosk partial")
                }
'''
if old_partial not in s:
    raise SystemExit('partial stop blogu bulunamadi')
s = s.replace(old_partial, new_partial, 1)

old_final = '''            stopDetected && activeRecording != null -> { lastVoiceCommandMs = now; voiceStopRequested = true; runOnUiThread { binding.tvVoice.text = "Komut alındı: ${stopWord.uppercase()}"; stopRecording() } }
'''
new_final = '''            stopDetected -> { lastVoiceCommandMs = now; requestVoiceStop("Vosk final") }
'''
if old_final not in s:
    raise SystemExit('final stop blogu bulunamadi')
s = s.replace(old_final, new_final, 1)

s = s.replace('''                override fun onError(exception: Exception?) {
                    speechService = null
                    binding.tvVoice.text = "Sesli komut yeniden başlatılıyor"
''','''                override fun onError(exception: Exception?) {
                    speechService = null
                    val msg = exception?.let { it.javaClass.simpleName + ": " + (it.message ?: "") } ?: "bilinmeyen Vosk hatası"
                    try { getSharedPreferences("motocam_crash", MODE_PRIVATE).edit().putString("last_crash", "MotoCam sesli komut raporu\\n" + msg).apply() } catch (_: Throwable) {}
                    binding.tvVoice.text = "Sesli komut yeniden başlatılıyor"
''',1)

kt.write_text(s, encoding='utf-8')

g = Path('motocam/app/build.gradle.kts')
t = g.read_text(encoding='utf-8')
t = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 35', t, count=1)
t = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "4.5.0"', t, count=1)
g.write_text(t, encoding='utf-8')

print('MotoCam v4.5: verified voice-stop + non-crash logic diagnostics')
