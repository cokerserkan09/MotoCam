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

new = '''        val lastWord = words.lastOrNull()

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

if old not in text:
    raise SystemExit("v1.9 komut blogu bulunamadi")
text = text.replace(old, new, 1)

# Ekrandaki eski komut aciklamasini da guncelle.
text = text.replace('Sesli komut: “Başla” / “Dur”', 'Sesli komut: “BİR” / “İKİ”')
text = text.replace('Sesli komut: "Başla" / "Dur"', 'Sesli komut: "BİR" / "İKİ"')

# Surumu 2.0 yap.
gradle = Path("motocam/app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
g = g.replace("versionCode = 9", "versionCode = 10")
g = g.replace('versionName = "1.9.0"', 'versionName = "2.0.0"')
gradle.write_text(g, encoding="utf-8")

kt.write_text(text, encoding="utf-8")
print("MotoCam v2.0: son duyulan kelime IKI ise stop, BIR ise start.")
