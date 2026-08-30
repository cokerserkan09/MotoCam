from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')

# ---- Persistent automatic segmented-recording settings ----
anchor = '    private fun micSource(): String = commandPrefs.getString("mic_source", "phone") ?: "phone"\n'
if anchor not in s:
    raise SystemExit('micSource anchor bulunamadi')
helpers = '''    private fun autoSegmentEnabled(): Boolean = commandPrefs.getBoolean("segment_enabled", false)
    private fun segmentMinutes(): Int = commandPrefs.getInt("segment_minutes", 1).coerceIn(1, 120)
    private fun segmentGapSeconds(): Int = commandPrefs.getInt("segment_gap_seconds", 2).coerceIn(1, 60)
    private fun segmentCount(): Int = commandPrefs.getInt("segment_count", 50).coerceIn(1, 999)

    private var segmentSequenceActive = false
    private var segmentIndex = 0
    private var segmentAutoStopping = false
    private var segmentStopRunnable: Runnable? = null
    private var segmentRestartRunnable: Runnable? = null

    private fun cancelSegmentSequence() {
        segmentSequenceActive = false
        segmentIndex = 0
        segmentAutoStopping = false
        segmentStopRunnable?.let { binding.root.removeCallbacks(it) }
        segmentRestartRunnable?.let { binding.root.removeCallbacks(it) }
        segmentStopRunnable = null
        segmentRestartRunnable = null
    }

    private fun scheduleSegmentStopIfNeeded() {
        if (!segmentSequenceActive || !autoSegmentEnabled()) return
        segmentStopRunnable?.let { binding.root.removeCallbacks(it) }
        val durationMs = segmentMinutes().toLong() * 60_000L
        binding.tvVoice.text = "Otomatik kayıt: $segmentIndex/${segmentCount()} • ${segmentMinutes()} dk"
        segmentStopRunnable = Runnable {
            if (segmentSequenceActive && activeRecording != null) {
                segmentAutoStopping = true
                stopRecording()
            }
        }
        binding.root.postDelayed(segmentStopRunnable!!, durationMs)
    }

    private fun handleSegmentFinalized(hadError: Boolean) {
        segmentStopRunnable?.let { binding.root.removeCallbacks(it) }
        segmentStopRunnable = null
        if (!segmentSequenceActive) return
        if (hadError) {
            cancelSegmentSequence()
            binding.tvVoice.text = "Otomatik kayıt hata nedeniyle durdu"
            return
        }
        if (!segmentAutoStopping) {
            cancelSegmentSequence()
            return
        }
        segmentAutoStopping = false
        val targetCount = segmentCount()
        if (segmentIndex >= targetCount) {
            val completed = segmentIndex
            cancelSegmentSequence()
            binding.tvVoice.text = "Otomatik kayıt tamamlandı: $completed video"
            return
        }
        val nextIndex = segmentIndex + 1
        val gapMs = segmentGapSeconds().toLong() * 1000L
        binding.tvVoice.text = "Video $segmentIndex/$targetCount kaydedildi • ${segmentGapSeconds()} sn sonra devam"
        segmentRestartRunnable = Runnable {
            if (!segmentSequenceActive) return@Runnable
            segmentIndex = nextIndex
            startRecording()
        }
        binding.root.postDelayed(segmentRestartRunnable!!, gapMs)
    }

'''
if 'private fun autoSegmentEnabled()' not in s:
    s = s.replace(anchor, anchor + helpers, 1)

# ---- Add segmented recording controls to Settings ----
settings_start = s.find('    private fun showCommandSettings() {')
settings_end = s.find('    private fun playRecordingStartedSound()', settings_start)
if settings_start < 0 or settings_end < 0:
    raise SystemExit('showCommandSettings bulunamadi')
block = s[settings_start:settings_end]

needle = '        box.addView(startInput); box.addView(stopInput); box.addView(controlTitle); box.addView(group)\n'
if needle not in block:
    raise SystemExit('settings controls anchor bulunamadi')
segment_ui = '''        val segmentTitle = android.widget.TextView(this).apply {
            text = "Otomatik parçalı kayıt"
            textSize = 17f
            setPadding(0, (14 * resources.displayMetrics.density).toInt(), 0, (6 * resources.displayMetrics.density).toInt())
        }
        val segmentEnabled = android.widget.CheckBox(this).apply {
            text = "Süre dolunca kaydet ve otomatik devam et"
            isChecked = autoSegmentEnabled()
        }
        val durationInput = android.widget.EditText(this).apply {
            hint = "Her videonun süresi (dakika)"
            setText(segmentMinutes().toString())
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
        }
        val gapInput = android.widget.EditText(this).apply {
            hint = "Videolar arası bekleme (saniye)"
            setText(segmentGapSeconds().toString())
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
        }
        val countInput = android.widget.EditText(this).apply {
            hint = "Kaç video kaydedilsin?"
            setText(segmentCount().toString())
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
        }
        box.addView(startInput); box.addView(stopInput); box.addView(controlTitle); box.addView(group)
        box.addView(segmentTitle); box.addView(segmentEnabled); box.addView(durationInput); box.addView(gapInput); box.addView(countInput)
'''
block = block.replace(needle, segment_ui, 1)

save_needle = '                    commandPrefs.edit().putString("start_command", startWord).putString("stop_command", stopWord).putString("mic_source", mode).apply()\n'
if save_needle not in block:
    raise SystemExit('settings save anchor bulunamadi')
save_repl = '''                    val minutes = durationInput.text.toString().toIntOrNull()?.coerceIn(1, 120) ?: 1
                    val gapSeconds = gapInput.text.toString().toIntOrNull()?.coerceIn(1, 60) ?: 2
                    val videos = countInput.text.toString().toIntOrNull()?.coerceIn(1, 999) ?: 50
                    commandPrefs.edit()
                        .putString("start_command", startWord)
                        .putString("stop_command", stopWord)
                        .putString("mic_source", mode)
                        .putBoolean("segment_enabled", segmentEnabled.isChecked)
                        .putInt("segment_minutes", minutes)
                        .putInt("segment_gap_seconds", gapSeconds)
                        .putInt("segment_count", videos)
                        .apply()
'''
block = block.replace(save_needle, save_repl, 1)
block = block.replace('.setView(box)', '.setView(android.widget.ScrollView(this).apply { addView(box) })', 1)
s = s[:settings_start] + block + s[settings_end:]

# ---- Start a sequence automatically whenever any control method starts a recording ----
start_marker = '    private fun startRecording() {\n'
if start_marker not in s:
    raise SystemExit('startRecording bulunamadi')
start_insert = '''    private fun startRecording() {
        if (!segmentSequenceActive && autoSegmentEnabled()) {
            segmentSequenceActive = true
            segmentIndex = 1
            segmentAutoStopping = false
        }
'''
s = s.replace(start_marker, start_insert, 1)

# Start the timer only after CameraX confirms recording has really begun.
started_marker = '        binding.tvStatus.text = "● KAYIT"\n        playRecordingStartedSound()\n'
if started_marker not in s:
    raise SystemExit('onRecordingStarted anchor bulunamadi')
s = s.replace(started_marker, started_marker + '        scheduleSegmentStopIfNeeded()\n', 1)

# Manual stop cancels the rest of the sequence; automatic segment stop is allowed to continue.
stop_marker = '    private fun stopRecording() {\n'
if stop_marker not in s:
    raise SystemExit('stopRecording bulunamadi')
stop_insert = '''    private fun stopRecording() {
        if (segmentSequenceActive && !segmentAutoStopping) cancelSegmentSequence()
'''
s = s.replace(stop_marker, stop_insert, 1)

# When a segment has finalized and is safely saved, schedule the next segment after the configured gap.
final_anchor = '        val trimVoiceTail = voiceStopRequested; voiceStopRequested = false\n'
if final_anchor not in s:
    raise SystemExit('finalize anchor bulunamadi')
s = s.replace(final_anchor, final_anchor + '        handleSegmentFinalized(event.hasError())\n', 1)

kt.write_text(s, encoding='utf-8')

gradle = Path('motocam/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 24', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "3.3.0"', g, count=1)
gradle.write_text(g, encoding='utf-8')

print('MotoCam v3.3: ayarlanabilir sure/adet/aralik ile otomatik parcali kayit')
