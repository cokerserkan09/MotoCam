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
                    playRecordingStoppedSound()
                    stopRecording()
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

text = text.replace('Sesli komut: “Başla” / “Dur”', 'Sesli komut: “BİR” / “SERKAN”')
text = text.replace('Sesli komut: "Başla" / "Dur"', 'Sesli komut: "BİR" / "SERKAN"')

# Surumu 2.3 yap.
gradle = Path("motocam/app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
g = g.replace("versionCode = 9", "versionCode = 13")
g = g.replace("versionCode = 10", "versionCode = 13")
g = g.replace('versionName = "1.9.0"', 'versionName = "2.3.0"')
g = g.replace('versionName = "2.0.0"', 'versionName = "2.3.0"')
gradle.write_text(g, encoding="utf-8")

kt.write_text(text, encoding="utf-8")
print("MotoCam v2.3: BIR baslatir, SERKAN durdurur ve durdurma sesi komut aninda calar.")
