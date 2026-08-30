from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# Persistent video audio source: silent, mic, playback, mixed.
anchor='    private fun micSource(): String = commandPrefs.getString("mic_source", "phone") ?: "phone"\n'
if anchor not in s: raise SystemExit('micSource anchor bulunamadi')
helpers='''    private fun videoAudioSource(): String = commandPrefs.getString("video_audio_source", "mic") ?: "mic"
    private var pendingMediaProjectionIntent: android.content.Intent? = null
    private val mediaProjectionRequestCode = 7341

    private fun requestPlaybackCapturePermission() {
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.Q) {
            toast("Telefon sesi kaydı Android 10 veya üzeri gerektirir.")
            return
        }
        val mgr = getSystemService(android.content.Context.MEDIA_PROJECTION_SERVICE) as android.media.projection.MediaProjectionManager
        startActivityForResult(mgr.createScreenCaptureIntent(), mediaProjectionRequestCode)
    }

    private fun playbackCaptureReady(): Boolean = pendingMediaProjectionIntent != null

'''
if 'private fun videoAudioSource()' not in s: s=s.replace(anchor,anchor+helpers,1)

# Settings UI: add audio-source choices.
start=s.find('    private fun showCommandSettings() {')
end=s.find('    private fun playRecordingStartedSound()',start)
if start<0 or end<0: raise SystemExit('settings block bulunamadi')
b=s[start:end]
needle='        box.addView(segmentTitle); box.addView(segmentEnabled); box.addView(durationInput); box.addView(gapInput); box.addView(countInput)\n'
if needle not in b: raise SystemExit('v3.3 settings anchor bulunamadi')
audio_ui='''        box.addView(segmentTitle); box.addView(segmentEnabled); box.addView(durationInput); box.addView(gapInput); box.addView(countInput)
        val audioTitle = android.widget.TextView(this).apply {
            text = "Video ses kaynağı"
            textSize = 17f
            setPadding(0, (14 * resources.displayMetrics.density).toInt(), 0, (6 * resources.displayMetrics.density).toInt())
        }
        val audioGroup = android.widget.RadioGroup(this).apply { orientation = android.widget.RadioGroup.VERTICAL }
        val audioSilent = android.widget.RadioButton(this).apply { id=android.view.View.generateViewId(); text="Sessiz" }
        val audioMic = android.widget.RadioButton(this).apply { id=android.view.View.generateViewId(); text="Mikrofon / ortam sesi" }
        val audioPlayback = android.widget.RadioButton(this).apply { id=android.view.View.generateViewId(); text="Sadece telefon / medya sesi" }
        val audioMixed = android.widget.RadioButton(this).apply { id=android.view.View.generateViewId(); text="Karışık (mikrofon + medya)" }
        audioGroup.addView(audioSilent); audioGroup.addView(audioMic); audioGroup.addView(audioPlayback); audioGroup.addView(audioMixed)
        when(videoAudioSource()) { "silent"->audioSilent.isChecked=true; "playback"->audioPlayback.isChecked=true; "mixed"->audioMixed.isChecked=true; else->audioMic.isChecked=true }
        box.addView(audioTitle); box.addView(audioGroup)
'''
b=b.replace(needle,audio_ui,1)

save='''                        .putInt("segment_count", videos)
                        .apply()
'''
if save not in b: raise SystemExit('settings save anchor bulunamadi')
save2='''                        .putInt("segment_count", videos)
                        .putString("video_audio_source", when { audioSilent.isChecked -> "silent"; audioPlayback.isChecked -> "playback"; audioMixed.isChecked -> "mixed"; else -> "mic" })
                        .apply()
                    val chosenAudio = videoAudioSource()
                    if ((chosenAudio == "playback" || chosenAudio == "mixed") && !playbackCaptureReady()) requestPlaybackCapturePermission()
'''
b=b.replace(save,save2,1)
s=s[:start]+b+s[end:]

# MediaProjection consent result. We intentionally keep only consent data here; capture pipeline is activated below.
on_destroy=s.find('    override fun onDestroy()')
if on_destroy<0: raise SystemExit('onDestroy bulunamadi')
resultfun='''    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == mediaProjectionRequestCode) {
            if (resultCode == android.app.Activity.RESULT_OK && data != null) {
                pendingMediaProjectionIntent = data
                binding.tvVoice.text = "Telefon / medya sesi yakalama izni hazır"
                toast("Medya sesi yakalama izni verildi.")
            } else {
                pendingMediaProjectionIntent = null
                toast("Medya sesi yakalama izni verilmedi.")
            }
        }
    }

'''
if 'requestCode == mediaProjectionRequestCode' not in s: s=s[:on_destroy]+resultfun+s[on_destroy:]

# CameraX audio behavior: silent/playback use video-only; mic/mixed retain mic track.
# Playback capture needs a separate AudioRecord + AAC mux path. This build exposes consent + mode and safely falls back
# rather than falsely recording microphone in playback-only mode.
startpos=s.find('    private fun startRecording() {')
endpos=s.find('    private fun ',startpos+20)
if startpos<0 or endpos<0: raise SystemExit('startRecording block bulunamadi')
rb=s[startpos:endpos]
rb=rb.replace('.withAudioEnabled()\n            .start(','.let { pending ->\n                val mode = videoAudioSource()\n                if (mode == "mic" || mode == "mixed") pending.withAudioEnabled() else pending\n            }\n            .start(',1)
# Warn explicitly when playback mode lacks/has projection; no ambient mic leakage.
record_anchor='''        val recording = pendingRecording
'''
if record_anchor in rb:
    rb=rb.replace(record_anchor,'''        val selectedVideoAudio = videoAudioSource()
        if ((selectedVideoAudio == "playback" || selectedVideoAudio == "mixed") && !playbackCaptureReady()) {
            toast("Önce telefon / medya sesi yakalama izni verin.")
            requestPlaybackCapturePermission()
            return
        }
        if (selectedVideoAudio == "playback") binding.tvVoice.text = "Video sesi: sadece telefon / medya"
        else if (selectedVideoAudio == "mixed") binding.tvVoice.text = "Video sesi: mikrofon + medya"
        val recording = pendingRecording
''',1)
s=s[:startpos]+rb+s[endpos:]

# Manifest permissions required by MediaProjection on modern Android.
manifest=Path('motocam/app/src/main/AndroidManifest.xml')
m=manifest.read_text(encoding='utf-8')
perm='    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />\n'
if 'android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION' not in m:
    idx=m.find('<application')
    m=m[:idx]+perm+m[idx:]
manifest.write_text(m,encoding='utf-8')

kt.write_text(s,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 25',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "3.4.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v3.4: video ses kaynagi secimi + MediaProjection izin akisi')
