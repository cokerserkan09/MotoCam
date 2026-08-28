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

new = '''        val commandText = normalized
            .replace("İ", "i")
            .replace("I", "ı")
            .trim()
        val lastWord = words.lastOrNull()
        val ikiDetected = lastWord == "iki" || words.contains("iki") || commandText == "iki" || commandText.endsWith(" iki")
        val birDetected = lastWord == "bir" || words.contains("bir") || commandText == "bir" || commandText.endsWith(" bir")

        when {
            ikiDetected -> {
                lastVoiceCommandMs = now
                runOnUiThread {
                    binding.tvVoice.text = "Komut alındı: İKİ"
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

if old not in text:
    # v2.0 uygulanmis kaynak icin mevcut blogu degistir.
    old2 = '''        val lastWord = words.lastOrNull()

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
    if old2 not in text:
        raise SystemExit("komut blogu bulunamadi")
    text = text.replace(old2, new, 1)
else:
    text = text.replace(old, new, 1)

text = text.replace('Sesli komut: “Başla” / “Dur”', 'Sesli komut: “BİR” / “İKİ”')
text = text.replace('Sesli komut: "Başla" / "Dur"', 'Sesli komut: "BİR" / "İKİ"')

# Surumu 2.1 yap.
gradle = Path("motocam/app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
g = g.replace("versionCode = 9", "versionCode = 11")
g = g.replace("versionCode = 10", "versionCode = 11")
g = g.replace('versionName = "1.9.0"', 'versionName = "2.1.0"')
g = g.replace('versionName = "2.0.0"', 'versionName = "2.1.0"')
gradle.write_text(g, encoding="utf-8")

kt.write_text(text, encoding="utf-8")
print("MotoCam v2.1: IKI birden fazla yontemle algilanir ve stop ana thread uzerinden calisir.")
