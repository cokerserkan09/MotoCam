from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')

# A Vosk partial stop can be followed by the same final result after CameraX has
# already finalized. Treat that as the same command, not as a recording-state error.
old = '''    private fun requestVoiceStop(source: String) {
        runOnUiThread {
            val stopWord = stopCommand()
            val before = activeRecording
            binding.tvVoice.text = "Komut alındı: ${stopWord.uppercase()} • durduruluyor"
            if (before == null) {
                reportMotoCamLogicIssue("Durdurma kelimesi algılandı ($source) fakat activeRecording null. Kayıt durumu ile CameraX nesnesi uyuşmuyor.")
                return@runOnUiThread
            }
'''
new = '''    private fun requestVoiceStop(source: String) {
        runOnUiThread {
            val stopWord = stopCommand()
            val before = activeRecording
            binding.tvVoice.text = "Komut alındı: ${stopWord.uppercase()} • durduruluyor"
            if (before == null) {
                // Vosk commonly emits partial first and the same command again as final.
                // If recording has just finalized, this is a duplicate success signal.
                val duplicateWindow = android.os.SystemClock.elapsedRealtime() - lastVoiceCommandMs < 5000L
                val recordingAlreadyFinished = binding.tvStatus.text?.toString()?.contains("Video kaydedildi", ignoreCase = true) == true
                if (duplicateWindow && recordingAlreadyFinished) {
                    binding.tvVoice.text = "Komut tamamlandı: ${stopWord.uppercase()}"
                    return@runOnUiThread
                }
                reportMotoCamLogicIssue("Durdurma kelimesi algılandı ($source) fakat activeRecording null ve kayıt henüz tamamlanmış görünmüyor. Kayıt durumu ile CameraX nesnesi uyuşmuyor.")
                return@runOnUiThread
            }
'''
if old not in s:
    raise SystemExit('v4.5 requestVoiceStop blogu bulunamadi')
s = s.replace(old, new, 1)

# Do not allow final/full Vosk result to re-fire the same command after a partial
# already accepted it. This also avoids overwriting the successful finalize state.
old_final = '''            stopDetected -> { lastVoiceCommandMs = now; requestVoiceStop("Vosk final") }
'''
new_final = '''            stopDetected -> {
                if (now - lastVoiceCommandMs >= 2500L) {
                    lastVoiceCommandMs = now
                    requestVoiceStop("Vosk final")
                }
            }
'''
if old_final not in s:
    raise SystemExit('v4.5 final stop blogu bulunamadi')
s = s.replace(old_final, new_final, 1)

# Version bump; keep permanent crash/logic diagnostics from v4.3/v4.5.
g = Path('motocam/app/build.gradle.kts')
t = g.read_text(encoding='utf-8')
t = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 36', t, count=1)
t = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "4.6.0"', t, count=1)
g.write_text(t, encoding='utf-8')
kt.write_text(s, encoding='utf-8')
print('MotoCam v4.6: Vosk partial/final duplicate stop dedupe + diagnostics preserved')
