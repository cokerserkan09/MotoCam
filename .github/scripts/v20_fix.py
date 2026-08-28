from pathlib import Path

kt = Path("motocam/app/src/main/java/com/motocam/app/MainActivity.kt")
text = kt.read_text(encoding="utf-8")

old = '''        when {
            words.contains("bir") -> {
                if (activeRecording == null) {
                    lastVoiceCommandMs = now
                    startRecording()
                    binding.tvVoice.text = "Komut alındı: BİR"
                }
            }

            words.contains("iki") -> {
                lastVoiceCommandMs = now
                binding.tvVoice.text = "Komut alındı: İKİ"
                stopRecording()
            }
        }
'''

new = '''        val commandText = normalized.trim()
        val lastWord = words.lastOrNull()
        val serkanDetected = lastWord == "serkan" || words.contains("serkan") || commandText == "serkan" || commandText.endsWith(" serkan")
        val birDetected = lastWord == "bir" || words.contains("bir") || commandText == "bir" || commandText.endsWith(" bir")

        when {
            serkanDetected -> {
                lastVoiceCommandMs = now
                runOnUiThread {
                    binding.tvVoice.text = "Komut alındı: SERKAN"
                    stopRecording()
                    binding.root.postDelayed({
                        playRecordingStoppedSound()
                        binding.root.postDelayed({ playRecordingStoppedSound() }, 380)
                    }, 700)
                }
            }

            birDetected -> {
                if (activeRecording == null) {
                    lastVoiceCommandMs = now
                    runOnUiThread {
                        startRecording()
                        binding.tvVoice.text = "Komut alındı: BİR"
                    }
                }
            }
        }
'''

old_v20 = '''        val lastWord = words.lastOrNull()

        when {
            lastWord == "iki" -> {
                lastVoiceCommandMs = now
                binding.tvVoice.text = "Komut alındı: İKİ"
                stopRecording()
            }

            lastWord == "bir" -> {
                if (activeRecording == null) {
                    lastVoiceCommandMs = now
                    startRecording()
                    binding.tvVoice.text = "Komut alındı: BİR"
                }
            }
        }
'''

if old_v20 in text:
    text = text.replace(old_v20, new, 1)
elif old in text:
    text = text.replace(old, new, 1)
else:
    raise SystemExit("komut blogu bulunamadi")

start_pos = text.find("    private fun startRecording() {")
if start_pos == -1:
    raise SystemExit("startRecording bulunamadi")
end_pos = text.find("    private fun ", start_pos + 10)
if end_pos == -1:
    end_pos = len(text)
block = text[start_pos:end_pos]
if ".withAudioEnabled()" not in block:
    start_call = block.find(".start(")
    if start_call == -1:
        raise SystemExit("startRecording icinde .start( bulunamadi")
    block = block[:start_call] + ".withAudioEnabled()\n            " + block[start_call:]
    text = text[:start_pos] + block + text[end_pos:]

text = text.replace('Sesli komut: “Başla” / “Dur”', 'Sesli komut: “BİR” / “SERKAN”')
text = text.replace('Sesli komut: "Başla" / "Dur"', 'Sesli komut: "BİR" / "SERKAN"')

gradle = Path("motocam/app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
g = g.replace("versionCode = 9", "versionCode = 14")
g = g.replace('versionName = "1.9.0"', 'versionName = "2.4.0"')
gradle.write_text(g, encoding="utf-8")

kt.write_text(text, encoding="utf-8")
print("MotoCam v2.4 hazir")
