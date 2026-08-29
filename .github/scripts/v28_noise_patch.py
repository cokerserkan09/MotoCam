from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
text = kt.read_text(encoding='utf-8')

# In traffic/wind, Vosk partial hypotheses are very noisy. Only execute commands
# from completed recognition results and require an exact configured command token.
text = text.replace('''                override fun onPartialResult(hypothesis: String?) {
                    handleVoskResult(hypothesis)
                }

                override fun onResult(hypothesis: String?) {
                    handleVoskResult(hypothesis)
                }

                override fun onFinalResult(hypothesis: String?) {
                    handleVoskResult(hypothesis)
                }
''','''                override fun onPartialResult(hypothesis: String?) {
                    // Ruzgar/motor gurultusunde partial sonuclar yanlis kelime uretebilir.
                    // Komut calistirma; sadece tamamlanmis sonucu bekle.
                }

                override fun onResult(hypothesis: String?) {
                    handleVoskResult(hypothesis)
                }

                override fun onFinalResult(hypothesis: String?) {
                    handleVoskResult(hypothesis)
                }
''',1)

# Parse only final text, not partial text, for command execution.
old_parse = '''            val partial = obj.optString("partial", "")
            if (partial.isNotBlank()) partial else obj.optString("text", "")'''
new_parse = '''            obj.optString("text", "")'''
if old_parse in text:
    text = text.replace(old_parse, new_parse, 1)

# Tighten v2.5 configurable command matching. Do not accept arbitrary accumulated
# phrases ending in the command; require the completed utterance to be exactly
# the selected command, or a one-token result equal to it.
old = '''        val commandText = normalizeCommand(normalized)
        val lastWord = words.lastOrNull()?.let { normalizeCommand(it) }
        val startWord = startCommand(); val stopWord = stopCommand()
        val stopDetected = lastWord == stopWord || words.any { normalizeCommand(it) == stopWord } || commandText == stopWord || commandText.endsWith(" $stopWord")
        val startDetected = lastWord == startWord || words.any { normalizeCommand(it) == startWord } || commandText == startWord || commandText.endsWith(" $startWord")'''
new = '''        val commandText = normalizeCommand(normalized)
        val cleanWords = words.map { normalizeCommand(it) }.filter { it.isNotBlank() }
        val startWord = startCommand(); val stopWord = stopCommand()
        val stopDetected = commandText == stopWord || (cleanWords.size == 1 && cleanWords[0] == stopWord)
        val startDetected = commandText == startWord || (cleanWords.size == 1 && cleanWords[0] == startWord)'''
if old not in text:
    raise SystemExit('v2.7 command matching block bulunamadi')
text = text.replace(old, new, 1)

# Show active microphone route with device name on Android 12+.
old_bt = '''                    val ok = audioManager.setCommunicationDevice(btDevice)
                    binding.tvVoice.text = if (ok) "Bluetooth mikrofonu aktif" else "Bluetooth mikrofonu bağlanamadı"'''
new_bt = '''                    val ok = audioManager.setCommunicationDevice(btDevice)
                    val deviceName = btDevice.productName?.toString()?.takeIf { it.isNotBlank() } ?: "interkom"
                    binding.tvVoice.text = if (ok) "Aktif mikrofon: Bluetooth - $deviceName" else "Bluetooth mikrofonu bağlanamadı"'''
if old_bt in text:
    text = text.replace(old_bt, new_bt, 1)
text = text.replace('binding.tvVoice.text = "Telefon mikrofonu aktif"','binding.tvVoice.text = "Aktif mikrofon: Telefon"')

kt.write_text(text, encoding='utf-8')

gradle = Path('motocam/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 19', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.8.0"', g, count=1)
gradle.write_text(g, encoding='utf-8')
print('MotoCam v2.8: partial gurultu sonuclari engellendi, komut algilama sikilastirildi, aktif mikrofon gosterimi eklendi')
