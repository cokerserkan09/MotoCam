from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')
svc = Path('motocam/app/src/main/java/com/motocam/app/PlaybackCaptureService.kt')
p = svc.read_text(encoding='utf-8')

# ---- Service state: do not tell the camera that playback audio is ready until AudioRecord really started. ----
p = p.replace('''        @Volatile var projectionAlive = false\n''', '''        @Volatile var projectionAlive = false\n        @Volatile var captureReady = false\n        @Volatile var lastError: String? = null\n''', 1)

# Never let an exception in onStartCommand kill the whole MotoCam process.
old = '''    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {\n        when (intent?.action) {\n            ACTION_START -> startCapture(intent)\n            ACTION_STOP -> stopCapture(intent)\n        }\n        return START_NOT_STICKY\n    }\n'''
new = '''    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {\n        try {\n            when (intent?.action) {\n                ACTION_START -> startCapture(intent)\n                ACTION_STOP -> stopCapture(intent)\n            }\n        } catch (t: Throwable) {\n            lastError = t.javaClass.simpleName + ": " + (t.message ?: "medya sesi baslatma hatasi")\n            captureReady = false\n            running.set(false)\n            try { projection?.stop() } catch (_: Throwable) {}\n            projection = null\n            projectionAlive = false\n            try { stopForeground(STOP_FOREGROUND_REMOVE) } catch (_: Throwable) {}\n            stopSelf()\n        }\n        return START_NOT_STICKY\n    }\n'''
if old not in p:
    raise SystemExit('onStartCommand anchor bulunamadi')
p = p.replace(old, new, 1)

# Reset error/readiness at each start.
p = p.replace('''    private fun startCapture(intent: Intent) {\n        if (running.get()) return\n        currentMode = intent.getStringExtra(EXTRA_MODE) ?: "playback"\n''', '''    private fun startCapture(intent: Intent) {\n        if (running.get()) return\n        captureReady = false\n        lastError = null\n        currentMode = intent.getStringExtra(EXTRA_MODE) ?: "playback"\n''', 1)

# MediaProjection tokens are one-shot on recent Android. Register a callback immediately and invalidate state if revoked.
needle = '''            projection = mgr.getMediaProjection(resultCode, data)\n            projectionAlive = projection != null\n'''
repl = '''            projection = mgr.getMediaProjection(resultCode, data)\n            projectionAlive = projection != null\n            projection?.registerCallback(object : MediaProjection.Callback() {\n                override fun onStop() {\n                    projectionAlive = false\n                    captureReady = false\n                    running.set(false)\n                    projection = null\n                }\n            }, Handler(Looper.getMainLooper()))\n'''
if needle not in p:
    raise SystemExit('MediaProjection anchor bulunamadi')
p = p.replace(needle, repl, 1)

# If the audio thread itself fails, expose the error and cleanly stop instead of silently continuing with a mute video.
old_thread = '''        captureThread = Thread {\n            try { captureAac(p, audioFile, currentMode == "mixed") }\n            catch (_: Throwable) { running.set(false) }\n        }.also { it.start() }\n'''
new_thread = '''        captureThread = Thread {\n            try {\n                captureAac(p, audioFile, currentMode == "mixed")\n            } catch (t: Throwable) {\n                lastError = t.javaClass.simpleName + ": " + (t.message ?: "AudioPlaybackCapture hatasi")\n                captureReady = false\n                running.set(false)\n                try { projection?.stop() } catch (_: Throwable) {}\n                projection = null\n                projectionAlive = false\n                stopSelf()\n            }\n        }.also { it.start() }\n'''
if old_thread not in p:
    raise SystemExit('captureThread anchor bulunamadi')
p = p.replace(old_thread, new_thread, 1)

# captureReady only after Android AudioRecord actually starts.
p = p.replace('''        playback.startRecording(); mic?.startRecording()\n        var ptsUs = 0L\n''', '''        playback.startRecording(); mic?.startRecording()\n        if (playback.recordingState != AudioRecord.RECORDSTATE_RECORDING) {\n            throw IllegalStateException("Telefon medya sesi AudioRecord baslatilamadi")\n        }\n        captureReady = true\n        var ptsUs = 0L\n''', 1)

# Clear readiness on stop.
p = p.replace('''        running.set(false)\n        Thread {\n''', '''        running.set(false)\n        captureReady = false\n        Thread {\n''', 1)

svc.write_text(p, encoding='utf-8')

# ---- Activity: foreground-service startup must never crash the Activity. Do not consume the projection token until service is ready. ----
old_start = '''        androidx.core.content.ContextCompat.startForegroundService(this, intent)\n        if (!PlaybackCaptureService.projectionAlive) pendingMediaProjectionIntent = null\n        return true\n'''
new_start = '''        return try {\n            androidx.core.content.ContextCompat.startForegroundService(this, intent)\n            true\n        } catch (t: Throwable) {\n            binding.tvVoice.text = "Medya sesi başlatılamadı: ${t.javaClass.simpleName}"\n            toast("Medya sesi başlatılamadı. İzni yeniden verin.")\n            false\n        }\n'''
if old_start not in s:
    raise SystemExit('startForegroundService anchor bulunamadi')
s = s.replace(old_start, new_start, 1)

# At the very beginning of recording, use a two-phase start: first start playback capture; only then start CameraX.
# v3.9 self-fix inserted a realPlaybackMode block at function start. Replace it with a readiness gate.
pattern = re.compile(r'''    private fun startRecording\(\) \{\n        val realPlaybackMode = videoAudioSource\(\)\n        if \(\(realPlaybackMode == "playback" \|\| realPlaybackMode == "mixed"\) && !startPlaybackCaptureIfNeeded\(\)\) \{\n            toast\("Medya sesi yakalama izni gerekli\."\)\n            requestPlaybackCapturePermission\(\)\n            return\n        \}\n''')
match = pattern.search(s)
if not match:
    raise SystemExit('v3.9 startRecording gate bulunamadi')
new_gate = '''    private fun startRecording() {\n        val realPlaybackMode = videoAudioSource()\n        if (realPlaybackMode == "playback" || realPlaybackMode == "mixed") {\n            if (!PlaybackCaptureService.captureReady) {\n                if (!playbackCaptureReady()) {\n                    toast("Telefon / medya sesi için Android yakalama izni gerekli.")\n                    requestPlaybackCapturePermission()\n                    return\n                }\n                if (!startPlaybackCaptureIfNeeded()) return\n                binding.tvVoice.text = "Medya sesi hazırlanıyor…"\n                binding.root.postDelayed({\n                    when {\n                        PlaybackCaptureService.captureReady -> {\n                            pendingMediaProjectionIntent = null\n                            startRecording()\n                        }\n                        PlaybackCaptureService.lastError != null -> {\n                            pendingMediaProjectionIntent = null\n                            val msg = PlaybackCaptureService.lastError ?: "bilinmeyen hata"\n                            binding.tvVoice.text = "Medya sesi başlatılamadı: $msg"\n                            toast("Medya sesi başlatılamadı. Android yakalama iznini tekrar verin.")\n                        }\n                        else -> {\n                            binding.root.postDelayed({\n                                if (PlaybackCaptureService.captureReady) {\n                                    pendingMediaProjectionIntent = null\n                                    startRecording()\n                                } else {\n                                    val msg = PlaybackCaptureService.lastError ?: "telefon medya sesi yakalamayı başlatmadı"\n                                    binding.tvVoice.text = "Medya sesi başlatılamadı: $msg"\n                                    toast("Medya sesi hazır değil; kayıt başlatılmadı.")\n                                }\n                            }, 1000)\n                        }\n                    }\n                }, 500)\n                return\n            }\n        }\n'''
s = s[:match.start()] + new_gate + s[match.end():]

# v3.4 also contains a later permission gate. Once captureReady is true it is redundant and can incorrectly request consent again.
s = s.replace('''        if ((selectedVideoAudio == "playback" || selectedVideoAudio == "mixed") && !playbackCaptureReady()) {\n            toast("Önce telefon / medya sesi yakalama izni verin.")\n            requestPlaybackCapturePermission()\n            return\n        }\n''', '''        if ((selectedVideoAudio == "playback" || selectedVideoAudio == "mixed") && !PlaybackCaptureService.captureReady) {\n            toast("Medya sesi henüz hazır değil.")\n            return\n        }\n''', 1)

kt.write_text(s, encoding='utf-8')

# Version
g = Path('motocam/app/build.gradle.kts')
t = g.read_text(encoding='utf-8')
t = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 30', t, count=1)
t = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "4.0.0"', t, count=1)
g.write_text(t, encoding='utf-8')

print('MotoCam v4.0: medya modu crash guard + AudioRecord readiness + fresh MediaProjection state')
