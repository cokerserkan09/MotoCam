from pathlib import Path

kt = Path("motocam/app/src/main/java/com/motocam/app/MainActivity.kt")
text = kt.read_text(encoding="utf-8")

for line in [
    "import android.speech.RecognitionListener\n",
    "import android.speech.RecognizerIntent\n",
    "import android.speech.SpeechRecognizer\n",
]:
    text = text.replace(line, "")

old_field = "    private var speechRecognizer: SpeechRecognizer? = null\n    private var voiceWanted = true\n"
new_field = """    private var voskModel: org.vosk.Model? = null
    private var speechService: org.vosk.android.SpeechService? = null
    private var voiceInitStarted = false
    private var lastVoiceCommandMs = 0L
    private var voiceWanted = true
"""
if old_field not in text:
    raise SystemExit("SpeechRecognizer field bulunamadi")
text = text.replace(old_field, new_field, 1)

start = text.find("    private fun startVoiceControl() {")
end = text.find("    private fun tryRouteBluetoothMic() {", start)
if start == -1 or end == -1:
    raise SystemExit("Sesli komut blogu bulunamadi")

replacement = '''    private fun startVoiceControl() {
        if (!voiceWanted || !hasMicPermission()) return

        tryRouteBluetoothMic()

        if (speechService != null) {
            binding.tvVoice.text = "Sesli komut: sürekli dinliyor"
            return
        }
        if (voiceInitStarted) return
        voiceInitStarted = true
        binding.tvVoice.text = "Sesli komut modeli hazırlanıyor..."

        org.vosk.android.StorageService.unpack(
            this,
            "model-tr",
            "model-tr",
            { model ->
                voiceInitStarted = false
                voskModel = model
                if (voiceWanted && binding.switchVoice.isChecked) {
                    startVoskListening()
                }
            },
            { exception ->
                voiceInitStarted = false
                binding.tvVoice.text = "Sesli komut modeli açılamadı"
                toast("Sesli komut hatası: ${exception.message ?: "bilinmeyen hata"}")
            }
        )
    }

    private fun startVoskListening() {
        if (!voiceWanted || !binding.switchVoice.isChecked || !hasMicPermission()) return
        val model = voskModel ?: return
        if (speechService != null) return

        try {
            val recognizer = org.vosk.Recognizer(model, 16000.0f)
            val service = org.vosk.android.SpeechService(recognizer, 16000.0f)
            speechService = service
            binding.tvVoice.text = "Sesli komut: sürekli dinliyor"
            service.startListening(object : org.vosk.android.RecognitionListener {
                override fun onPartialResult(hypothesis: String?) {
                    handleVoskResult(hypothesis)
                }

                override fun onResult(hypothesis: String?) {
                    handleVoskResult(hypothesis)
                }

                override fun onFinalResult(hypothesis: String?) {
                    handleVoskResult(hypothesis)
                }

                override fun onError(exception: Exception?) {
                    speechService = null
                    binding.tvVoice.text = "Sesli komut yeniden başlatılıyor"
                    if (voiceWanted && binding.switchVoice.isChecked) {
                        binding.root.postDelayed({ startVoskListening() }, 800)
                    }
                }

                override fun onTimeout() {
                    speechService = null
                    if (voiceWanted && binding.switchVoice.isChecked) {
                        binding.root.postDelayed({ startVoskListening() }, 200)
                    }
                }
            })
        } catch (e: Exception) {
            speechService = null
            binding.tvVoice.text = "Sesli komut başlatılamadı"
            toast("Sesli komut hatası: ${e.message ?: "bilinmeyen hata"}")
        }
    }

    private fun handleVoskResult(json: String?) {
        if (json.isNullOrBlank()) return
        val spoken = try {
            val obj = org.json.JSONObject(json)
            val partial = obj.optString("partial", "")
            if (partial.isNotBlank()) partial else obj.optString("text", "")
        } catch (_: Exception) {
            ""
        }
        if (spoken.isBlank()) return

        val normalized = spoken.lowercase(Locale.ROOT)
        binding.tvVoice.text = "Duyuldu: $spoken"

        val now = System.currentTimeMillis()
        if (now - lastVoiceCommandMs < 1200L) return

        val words = normalized
            .replace(Regex("[^a-z ]"), " ")
            .split(Regex("\\s+"))
            .filter { it.isNotBlank() }

        when {
            words.contains("star") -> {
                if (activeRecording == null) {
                    lastVoiceCommandMs = now
                    startRecording()
                    binding.tvVoice.text = "Komut alındı: STAR"
                }
            }

            words.contains("stop") -> {
                if (activeRecording != null) {
                    lastVoiceCommandMs = now
                    stopRecording()
                    binding.tvVoice.text = "Komut alındı: STOP"
                }
            }
        }
    }

    private fun stopVoiceControl() {
        try { speechService?.stop() } catch (_: Exception) {}
        try { speechService?.shutdown() } catch (_: Exception) {}
        speechService = null
    }

'''
text = text[:start] + replacement + text[end:]

# Kayıt başladığında ve bittiğinde interkomdan duyulacak kısa onay tonları.
helper_marker = "    private fun startRecording() {"
helpers = '''    private fun playRecordingStartedSound() {
        try {
            val tone = android.media.ToneGenerator(android.media.AudioManager.STREAM_MUSIC, 90)
            tone.startTone(android.media.ToneGenerator.TONE_PROP_ACK, 220)
            uiHandler.postDelayed({ try { tone.release() } catch (_: Exception) {} }, 350)
        } catch (_: Exception) {}
    }

    private fun playRecordingStoppedSound() {
        try {
            val tone = android.media.ToneGenerator(android.media.AudioManager.STREAM_MUSIC, 90)
            tone.startTone(android.media.ToneGenerator.TONE_PROP_NACK, 300)
            uiHandler.postDelayed({ try { tone.release() } catch (_: Exception) {} }, 450)
        } catch (_: Exception) {}
    }

'''
if helper_marker in text and "private fun playRecordingStartedSound" not in text:
    text = text.replace(helper_marker, helpers + helper_marker, 1)

started_marker = '        binding.tvStatus.text = "● KAYIT"\n'
if started_marker in text and "playRecordingStartedSound()" not in text[text.find("private fun onRecordingStarted"):text.find("private fun onRecordingFinalized")]:
    text = text.replace(started_marker, started_marker + "        playRecordingStartedSound()\n", 1)

finalized_marker = '        binding.switchStabilization.isEnabled = true\n'
finalized_start = text.find("private fun onRecordingFinalized")
if finalized_start != -1:
    finalized_end = text.find("    private fun stopRecording()", finalized_start)
    finalized_block = text[finalized_start:finalized_end]
    if "playRecordingStoppedSound()" not in finalized_block and finalized_marker in finalized_block:
        pos = text.find(finalized_marker, finalized_start)
        pos += len(finalized_marker)
        text = text[:pos] + "        playRecordingStoppedSound()\n" + text[pos:]

old_destroy = "        speechRecognizer?.destroy()\n        speechRecognizer = null\n"
new_destroy = "        stopVoiceControl()\n        try { voskModel?.close() } catch (_: Exception) {}\n        voskModel = null\n"
if old_destroy in text:
    text = text.replace(old_destroy, new_destroy, 1)
else:
    print("Uyari: eski onDestroy SpeechRecognizer satirlari bulunamadi")

kt.write_text(text, encoding="utf-8")

gradle = Path("motocam/app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
if "com.alphacephei:vosk-android" not in g:
    if "dependencies {\n" not in g:
        raise SystemExit("Gradle dependencies blogu bulunamadi")
    g = g.replace(
        "dependencies {\n",
        "dependencies {\n"
        "    implementation(\"net.java.dev.jna:jna:5.13.0@aar\")\n"
        "    implementation(\"com.alphacephei:vosk-android:0.3.47@aar\")\n",
        1,
    )
g = g.replace("versionCode = 2", "versionCode = 7")
g = g.replace('versionName = "1.0.0"', 'versionName = "1.7.0"')
gradle.write_text(g, encoding="utf-8")

manifest = Path("motocam/app/src/main/AndroidManifest.xml")
m = manifest.read_text(encoding="utf-8")
m = m.replace('    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />\n', "")
manifest.write_text(m, encoding="utf-8")

print("MotoCam v1.7: STAR/STOP komutlari ve kayit onay sesleri eklendi.")
