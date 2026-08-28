from pathlib import Path

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
text = kt.read_text(encoding='utf-8')

# Fields: persistent configurable commands + voice-stop trim flag.
marker = '    private fun playRecordingStartedSound() {'
fields = '''    private val commandPrefs by lazy { getSharedPreferences("motocam_commands", MODE_PRIVATE) }
    private var voiceStopRequested = false

    private fun normalizeCommand(value: String): String = value.trim().lowercase(java.util.Locale("tr", "TR"))
    private fun startCommand(): String = normalizeCommand(commandPrefs.getString("start_command", "bir") ?: "bir")
    private fun stopCommand(): String = normalizeCommand(commandPrefs.getString("stop_command", "serkan") ?: "serkan")

    private fun showCommandSettings() {
        if (activeRecording != null) {
            toast("Kayıt sırasında ayarlar değiştirilemez.")
            return
        }
        val box = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            val p = (20 * resources.displayMetrics.density).toInt()
            setPadding(p, p / 2, p, 0)
        }
        val startInput = android.widget.EditText(this).apply {
            hint = "Kaydı başlatma kelimesi"
            setText(startCommand())
            inputType = android.text.InputType.TYPE_CLASS_TEXT
        }
        val stopInput = android.widget.EditText(this).apply {
            hint = "Kaydı durdurma kelimesi"
            setText(stopCommand())
            inputType = android.text.InputType.TYPE_CLASS_TEXT
        }
        box.addView(startInput)
        box.addView(stopInput)
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("MotoCam Ayarları")
            .setMessage("Sesli kayıt komutlarını belirleyin.")
            .setView(box)
            .setPositiveButton("KAYDET") { _, _ ->
                val start = normalizeCommand(startInput.text.toString())
                val stop = normalizeCommand(stopInput.text.toString())
                if (start.isBlank() || stop.isBlank() || start == stop || start.contains(" ") || stop.contains(" ")) {
                    toast("İki farklı, tek kelimelik komut girin.")
                } else {
                    commandPrefs.edit().putString("start_command", start).putString("stop_command", stop).apply()
                    binding.tvVoice.text = "Komutlar: ${start.uppercase()} / ${stop.uppercase()}"
                    toast("Sesli komutlar kaydedildi.")
                }
            }
            .setNegativeButton("İPTAL", null)
            .show()
    }

'''
if 'private val commandPrefs by lazy' not in text:
    text = text.replace(marker, fields + marker, 1)

# Replace hard-coded command detector introduced by v2.4.
old = '''        val commandText = normalized.trim()
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
new = '''        val commandText = normalizeCommand(normalized)
        val lastWord = words.lastOrNull()?.let { normalizeCommand(it) }
        val startWord = startCommand()
        val stopWord = stopCommand()
        val stopDetected = lastWord == stopWord || words.any { normalizeCommand(it) == stopWord } || commandText == stopWord || commandText.endsWith(" $stopWord")
        val startDetected = lastWord == startWord || words.any { normalizeCommand(it) == startWord } || commandText == startWord || commandText.endsWith(" $startWord")

        when {
            stopDetected && activeRecording != null -> {
                lastVoiceCommandMs = now
                voiceStopRequested = true
                runOnUiThread {
                    binding.tvVoice.text = "Komut alındı: ${stopWord.uppercase()}"
                    stopRecording()
                }
            }
            startDetected && activeRecording == null -> {
                lastVoiceCommandMs = now
                runOnUiThread {
                    startRecording()
                    binding.tvVoice.text = "Komut alındı: ${startWord.uppercase()}"
                }
            }
        }
'''
if old not in text:
    raise SystemExit('v2.4 command block not found')
text = text.replace(old, new, 1)

# Finalize: trim tail only for voice stop, then play tone after file is no longer recording.
oldfin = '''        binding.switchStabilization.isEnabled = true
        playRecordingStoppedSound()

        if (event.hasError()) {'''
newfin = '''        binding.switchStabilization.isEnabled = true
        val trimVoiceTail = voiceStopRequested
        voiceStopRequested = false

        if (!event.hasError() && trimVoiceTail) {
            val savedUri = event.outputResults.outputUri
            Thread {
                trimVideoEnd(savedUri, 1700L)
                runOnUiThread { playRecordingStoppedSound() }
            }.start()
        } else {
            binding.root.postDelayed({ playRecordingStoppedSound() }, 350)
        }

        if (event.hasError()) {'''
if oldfin not in text:
    raise SystemExit('finalize block not found')
text = text.replace(oldfin, newfin, 1)

# Platform MediaExtractor/MediaMuxer tail trim, replacing original MediaStore bytes.
stop_marker = '    private fun stopRecording() {'
trimfun = '''    private fun trimVideoEnd(uri: android.net.Uri, trimMs: Long) {
        val temp = java.io.File(cacheDir, "motocam_trim_${System.currentTimeMillis()}.mp4")
        var extractor: android.media.MediaExtractor? = null
        var muxer: android.media.MediaMuxer? = null
        try {
            val retriever = android.media.MediaMetadataRetriever()
            retriever.setDataSource(this, uri)
            val durationMs = retriever.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
            retriever.release()
            if (durationMs <= trimMs + 700L) return
            val cutoffUs = (durationMs - trimMs) * 1000L

            extractor = android.media.MediaExtractor()
            contentResolver.openFileDescriptor(uri, "r")?.use { pfd -> extractor.setDataSource(pfd.fileDescriptor) } ?: return
            muxer = android.media.MediaMuxer(temp.absolutePath, android.media.MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val trackMap = mutableMapOf<Int, Int>()
            for (i in 0 until extractor.trackCount) {
                val format = extractor.getTrackFormat(i)
                trackMap[i] = muxer.addTrack(format)
                extractor.selectTrack(i)
            }
            muxer.start()
            val buffer = java.nio.ByteBuffer.allocate(2 * 1024 * 1024)
            val info = android.media.MediaCodec.BufferInfo()
            while (true) {
                val track = extractor.sampleTrackIndex
                if (track < 0) break
                val timeUs = extractor.sampleTime
                if (timeUs < 0 || timeUs >= cutoffUs) break
                buffer.clear()
                val size = extractor.readSampleData(buffer, 0)
                if (size < 0) break
                info.offset = 0
                info.size = size
                info.presentationTimeUs = timeUs
                info.flags = extractor.sampleFlags
                muxer.writeSampleData(trackMap[track] ?: break, buffer, info)
                extractor.advance()
            }
            muxer.stop(); muxer.release(); muxer = null
            extractor.release(); extractor = null
            contentResolver.openOutputStream(uri, "wt")?.use { out -> temp.inputStream().use { it.copyTo(out) } }
        } catch (_: Exception) {
        } finally {
            try { muxer?.release() } catch (_: Exception) {}
            try { extractor?.release() } catch (_: Exception) {}
            temp.delete()
        }
    }

'''
if 'private fun trimVideoEnd(' not in text:
    text = text.replace(stop_marker, trimfun + stop_marker, 1)

# Add visible Settings button programmatically after setContentView(binding.root).
needle = '        setContentView(binding.root)'
settings = '''        setContentView(binding.root)

        val settingsButton = android.widget.Button(this).apply {
            text = "AYARLAR"
            textSize = 12f
            setOnClickListener { showCommandSettings() }
        }
        (binding.root as? android.view.ViewGroup)?.addView(settingsButton, android.view.ViewGroup.LayoutParams(
            android.view.ViewGroup.LayoutParams.WRAP_CONTENT,
            android.view.ViewGroup.LayoutParams.WRAP_CONTENT
        ))'''
if 'text = "AYARLAR"' not in text:
    if needle not in text: raise SystemExit('setContentView not found')
    text = text.replace(needle, settings, 1)

# Version and hint.
text = text.replace('Sesli komut: “BİR” / “SERKAN”', 'Sesli komutlar AYARLAR bölümünden değiştirilebilir')
text = text.replace('Sesli komut: "BİR" / "SERKAN"', 'Sesli komutlar AYARLAR bölümünden değiştirilebilir')
kt.write_text(text, encoding='utf-8')

gradle = Path('motocam/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
import re
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 15', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.5.0"', g, count=1)
gradle.write_text(g, encoding='utf-8')
print('MotoCam v2.5 hazir: ayarlanabilir komutlar + sesli stop sonu temizleme')
