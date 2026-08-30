from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# MediaProjection sonuc kodunu da sakla ve servis canliysa izni hazir say.
s=s.replace('    private var pendingMediaProjectionIntent: android.content.Intent? = null\n    private val mediaProjectionRequestCode = 7341\n',
'''    private var pendingMediaProjectionIntent: android.content.Intent? = null
    private var pendingMediaProjectionResultCode: Int = android.app.Activity.RESULT_CANCELED
    private val mediaProjectionRequestCode = 7341
''',1)
s=s.replace('    private fun playbackCaptureReady(): Boolean = pendingMediaProjectionIntent != null\n',
'''    private fun playbackCaptureReady(): Boolean = pendingMediaProjectionIntent != null || PlaybackCaptureService.projectionAlive

    private fun startPlaybackCaptureIfNeeded(): Boolean {
        val mode = videoAudioSource()
        if (mode != "playback" && mode != "mixed") return true
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.Q) return false
        val intent = android.content.Intent(this, PlaybackCaptureService::class.java).apply {
            action = PlaybackCaptureService.ACTION_START
            putExtra(PlaybackCaptureService.EXTRA_MODE, mode)
            if (!PlaybackCaptureService.projectionAlive) {
                val data = pendingMediaProjectionIntent ?: return false
                putExtra(PlaybackCaptureService.EXTRA_RESULT_CODE, pendingMediaProjectionResultCode)
                putExtra(PlaybackCaptureService.EXTRA_PROJECTION_DATA, data)
            }
        }
        androidx.core.content.ContextCompat.startForegroundService(this, intent)
        if (!PlaybackCaptureService.projectionAlive) pendingMediaProjectionIntent = null
        return true
    }

    private fun stopPlaybackCaptureAndMux(uri: android.net.Uri, keepProjection: Boolean) {
        val mode = videoAudioSource()
        if (mode != "playback" && mode != "mixed") return
        val intent = android.content.Intent(this, PlaybackCaptureService::class.java).apply {
            action = PlaybackCaptureService.ACTION_STOP
            putExtra(PlaybackCaptureService.EXTRA_VIDEO_URI, uri.toString())
            putExtra(PlaybackCaptureService.EXTRA_KEEP_PROJECTION, keepProjection)
        }
        startService(intent)
    }

''',1)

# MediaProjection izin sonuc kodunu kaydet.
s=s.replace('                pendingMediaProjectionIntent = data\n                binding.tvVoice.text = "Telefon / medya sesi yakalama izni hazır"',
'''                pendingMediaProjectionIntent = data
                pendingMediaProjectionResultCode = resultCode
                binding.tvVoice.text = "Telefon / medya sesi yakalama izni hazır"''',1)

# mixed modunda CameraX mikrofonunu acma; mixed ses servis tarafinda olusturulacak.
s=s.replace('if (mode == "mic" || mode == "mixed") pending.withAudioEnabled() else pending',
            'if (mode == "mic") pending.withAudioEnabled() else pending',1)

# Kayit baslamadan once gercek playback capture servisini baslat.
needle='''        if (selectedVideoAudio == "playback") binding.tvVoice.text = "Video sesi: sadece telefon / medya"
        else if (selectedVideoAudio == "mixed") binding.tvVoice.text = "Video sesi: mikrofon + medya"
        val recording = pendingRecording
'''
repl='''        if (selectedVideoAudio == "playback") binding.tvVoice.text = "Video sesi: sadece telefon / medya"
        else if (selectedVideoAudio == "mixed") binding.tvVoice.text = "Video sesi: mikrofon + medya"
        if ((selectedVideoAudio == "playback" || selectedVideoAudio == "mixed") && !startPlaybackCaptureIfNeeded()) {
            toast("Medya sesi yakalama izni gerekli.")
            requestPlaybackCapturePermission()
            return
        }
        val recording = pendingRecording
'''
if needle not in s: raise SystemExit('startRecording playback anchor bulunamadi')
s=s.replace(needle,repl,1)

# Finalize aninda AAC sesini video ile mux et. Otomatik parcali kayitta projection acik kalabilir.
final='''        handleSegmentFinalized(event.hasError())
'''
if final not in s: raise SystemExit('finalize segment anchor bulunamadi')
final_repl='''        val keepPlaybackProjection = segmentSequenceActive && segmentAutoStopping && !event.hasError()
        if (!event.hasError()) stopPlaybackCaptureAndMux(event.outputResults.outputUri, keepPlaybackProjection)
        else if (videoAudioSource() == "playback" || videoAudioSource() == "mixed") {
            val stopIntent = android.content.Intent(this, PlaybackCaptureService::class.java).apply {
                action = PlaybackCaptureService.ACTION_STOP
                putExtra(PlaybackCaptureService.EXTRA_VIDEO_URI, "")
                putExtra(PlaybackCaptureService.EXTRA_KEEP_PROJECTION, false)
            }
            startService(stopIntent)
        }
        handleSegmentFinalized(event.hasError())
'''
s=s.replace(final,final_repl,1)
kt.write_text(s,encoding='utf-8')

service=Path('motocam/app/src/main/java/com/motocam/app/PlaybackCaptureService.kt')
service.write_text(r'''package com.motocam.app

import android.app.*
import android.content.*
import android.content.pm.ServiceInfo
import android.media.*
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.*
import java.io.File
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean

class PlaybackCaptureService : Service() {
    companion object {
        const val ACTION_START = "com.motocam.app.PLAYBACK_START"
        const val ACTION_STOP = "com.motocam.app.PLAYBACK_STOP"
        const val EXTRA_MODE = "mode"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_PROJECTION_DATA = "projection_data"
        const val EXTRA_VIDEO_URI = "video_uri"
        const val EXTRA_KEEP_PROJECTION = "keep_projection"
        @Volatile var projectionAlive = false
    }

    private val running = AtomicBoolean(false)
    private var projection: MediaProjection? = null
    private var captureThread: Thread? = null
    private var currentAudioFile: File? = null
    private var currentMode = "playback"

    override fun onBind(intent: Intent?) = null

    override fun onCreate() {
        super.onCreate()
        if (Build.VERSION.SDK_INT >= 26) {
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(NotificationChannel("motocam_media", "MotoCam medya sesi", NotificationManager.IMPORTANCE_LOW))
        }
    }

    private fun notification(text: String): Notification {
        val b = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, "motocam_media") else Notification.Builder(this)
        return b.setContentTitle("MotoCam").setContentText(text).setSmallIcon(android.R.drawable.ic_btn_speak_now).build()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startCapture(intent)
            ACTION_STOP -> stopCapture(intent)
        }
        return START_NOT_STICKY
    }

    @Suppress("DEPRECATION")
    private fun startCapture(intent: Intent) {
        if (running.get()) return
        currentMode = intent.getStringExtra(EXTRA_MODE) ?: "playback"
        val fgType = if (Build.VERSION.SDK_INT >= 29) {
            var t = ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            if (currentMode == "mixed") t = t or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            t
        } else 0
        if (Build.VERSION.SDK_INT >= 29) startForeground(3909, notification("Telefon / medya sesi kaydediliyor"), fgType)
        else startForeground(3909, notification("Telefon / medya sesi kaydediliyor"))

        if (projection == null) {
            val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED)
            val data = intent.getParcelableExtra(EXTRA_PROJECTION_DATA) as? Intent
            if (resultCode != Activity.RESULT_OK || data == null) { stopSelf(); return }
            val mgr = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            projection = mgr.getMediaProjection(resultCode, data)
            projectionAlive = projection != null
        }
        val p = projection ?: return
        currentAudioFile = File(cacheDir, "motocam_audio_${System.currentTimeMillis()}.m4a")
        running.set(true)
        val audioFile = currentAudioFile!!
        captureThread = Thread {
            try { captureAac(p, audioFile, currentMode == "mixed") }
            catch (_: Throwable) { running.set(false) }
        }.also { it.start() }
    }

    private fun stopCapture(intent: Intent) {
        val uriText = intent.getStringExtra(EXTRA_VIDEO_URI).orEmpty()
        val keepProjection = intent.getBooleanExtra(EXTRA_KEEP_PROJECTION, false)
        val audioFile = currentAudioFile
        running.set(false)
        Thread {
            try { captureThread?.join(5000) } catch (_: Throwable) {}
            captureThread = null
            currentAudioFile = null
            if (uriText.isNotBlank() && audioFile != null && audioFile.exists() && audioFile.length() > 0L) {
                try { muxIntoVideo(Uri.parse(uriText), audioFile) } catch (_: Throwable) {}
            }
            try { audioFile?.delete() } catch (_: Throwable) {}
            if (!keepProjection) {
                try { projection?.stop() } catch (_: Throwable) {}
                projection = null
                projectionAlive = false
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }.start()
    }

    private fun captureAac(p: MediaProjection, outFile: File, mixed: Boolean) {
        val sampleRate = 48000
        val channelMask = AudioFormat.CHANNEL_IN_MONO
        val encoding = AudioFormat.ENCODING_PCM_16BIT
        val min = AudioRecord.getMinBufferSize(sampleRate, channelMask, encoding).coerceAtLeast(4096)
        val bufferBytes = min * 2
        val fmt = AudioFormat.Builder().setEncoding(encoding).setSampleRate(sampleRate).setChannelMask(channelMask).build()
        val config = AudioPlaybackCaptureConfiguration.Builder(p)
            .addMatchingUsage(AudioAttributes.USAGE_MEDIA)
            .addMatchingUsage(AudioAttributes.USAGE_GAME)
            .addMatchingUsage(AudioAttributes.USAGE_UNKNOWN)
            .build()
        val playback = AudioRecord.Builder().setAudioFormat(fmt).setBufferSizeInBytes(bufferBytes).setAudioPlaybackCaptureConfig(config).build()
        val mic = if (mixed) AudioRecord(MediaRecorder.AudioSource.MIC, sampleRate, channelMask, encoding, bufferBytes) else null

        val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        val af = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, sampleRate, 1).apply {
            setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
            setInteger(MediaFormat.KEY_BIT_RATE, 128000)
            setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, bufferBytes)
        }
        codec.configure(af, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        codec.start()
        val muxer = MediaMuxer(outFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var muxTrack = -1
        var muxStarted = false
        val info = MediaCodec.BufferInfo()
        val pb = ShortArray(bufferBytes / 2)
        val mb = ShortArray(bufferBytes / 2)
        playback.startRecording(); mic?.startRecording()
        var ptsUs = 0L

        fun drain(eos: Boolean) {
            var idle = 0
            while (true) {
                val idx = codec.dequeueOutputBuffer(info, if (eos) 10000 else 0)
                when {
                    idx == MediaCodec.INFO_TRY_AGAIN_LATER -> { if (!eos || idle++ > 100) return }
                    idx == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                        muxTrack = muxer.addTrack(codec.outputFormat); muxer.start(); muxStarted = true
                    }
                    idx >= 0 -> {
                        val out = codec.getOutputBuffer(idx)
                        if (out != null && info.size > 0 && muxStarted && (info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG) == 0) {
                            out.position(info.offset); out.limit(info.offset + info.size); muxer.writeSampleData(muxTrack, out, info)
                        }
                        val end = (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0
                        codec.releaseOutputBuffer(idx, false)
                        if (end) return
                    }
                }
            }
        }

        while (running.get()) {
            val n = playback.read(pb, 0, pb.size)
            if (n <= 0) continue
            if (mixed) {
                val mn = mic?.read(mb, 0, n) ?: 0
                for (i in 0 until n) {
                    val a = pb[i].toInt(); val b = if (i < mn) mb[i].toInt() else 0
                    pb[i] = ((a + b) / 2).coerceIn(Short.MIN_VALUE.toInt(), Short.MAX_VALUE.toInt()).toShort()
                }
            }
            var queued = false
            while (!queued) {
                val input = codec.dequeueInputBuffer(10000)
                if (input >= 0) {
                    val ib = codec.getInputBuffer(input)!!
                    ib.clear(); ib.order(ByteOrder.LITTLE_ENDIAN); ib.asShortBuffer().put(pb, 0, n)
                    codec.queueInputBuffer(input, 0, n * 2, ptsUs, 0)
                    ptsUs += n.toLong() * 1_000_000L / sampleRate
                    queued = true
                }
            }
            drain(false)
        }
        playback.stop(); mic?.stop()
        playback.release(); mic?.release()
        var eosQueued = false
        while (!eosQueued) {
            val input = codec.dequeueInputBuffer(10000)
            if (input >= 0) { codec.queueInputBuffer(input, 0, 0, ptsUs, MediaCodec.BUFFER_FLAG_END_OF_STREAM); eosQueued = true }
        }
        drain(true)
        codec.stop(); codec.release()
        if (muxStarted) muxer.stop()
        muxer.release()
    }

    private fun muxIntoVideo(videoUri: Uri, audioFile: File) {
        val temp = File(cacheDir, "motocam_mux_${System.currentTimeMillis()}.mp4")
        val videoEx = MediaExtractor(); videoEx.setDataSource(this, videoUri, null)
        val audioEx = MediaExtractor(); audioEx.setDataSource(audioFile.absolutePath)
        var vi = -1; var ai = -1
        for (i in 0 until videoEx.trackCount) if ((videoEx.getTrackFormat(i).getString(MediaFormat.KEY_MIME) ?: "").startsWith("video/")) { vi = i; break }
        for (i in 0 until audioEx.trackCount) if ((audioEx.getTrackFormat(i).getString(MediaFormat.KEY_MIME) ?: "").startsWith("audio/")) { ai = i; break }
        if (vi < 0 || ai < 0) { videoEx.release(); audioEx.release(); return }
        val mux = MediaMuxer(temp.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        try {
            val mmr = MediaMetadataRetriever(); mmr.setDataSource(this, videoUri)
            val rot = mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)?.toIntOrNull() ?: 0
            if (rot != 0) mux.setOrientationHint(rot); mmr.release()
        } catch (_: Throwable) {}
        val vo = mux.addTrack(videoEx.getTrackFormat(vi)); val ao = mux.addTrack(audioEx.getTrackFormat(ai)); mux.start()
        val buf = java.nio.ByteBuffer.allocateDirect(2 * 1024 * 1024)
        val bi = MediaCodec.BufferInfo()
        fun copy(ex: MediaExtractor, src: Int, dst: Int) {
            ex.selectTrack(src)
            while (true) {
                buf.clear(); val n = ex.readSampleData(buf, 0); if (n < 0) break
                bi.offset = 0; bi.size = n; bi.presentationTimeUs = ex.sampleTime; bi.flags = ex.sampleFlags
                mux.writeSampleData(dst, buf, bi); ex.advance()
            }
            ex.unselectTrack(src)
        }
        copy(videoEx, vi, vo); copy(audioEx, ai, ao)
        mux.stop(); mux.release(); videoEx.release(); audioEx.release()
        contentResolver.openOutputStream(videoUri, "wt")!!.use { output -> temp.inputStream().use { it.copyTo(output) } }
        temp.delete()
    }

    override fun onDestroy() {
        running.set(false)
        try { projection?.stop() } catch (_: Throwable) {}
        projection = null; projectionAlive = false
        super.onDestroy()
    }
}
''',encoding='utf-8')

manifest=Path('motocam/app/src/main/AndroidManifest.xml')
m=manifest.read_text(encoding='utf-8')
for perm in ['android.permission.FOREGROUND_SERVICE','android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION','android.permission.FOREGROUND_SERVICE_MICROPHONE']:
    if perm not in m:
        idx=m.find('<application'); m=m[:idx]+f'    <uses-permission android:name="{perm}" />\n'+m[idx:]
service_decl='''        <service
            android:name=".PlaybackCaptureService"
            android:exported="false"
            android:foregroundServiceType="mediaProjection|microphone" />
'''
if '.PlaybackCaptureService' not in m:
    m=m.replace('</application>',service_decl+'    </application>',1)
manifest.write_text(m,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 30',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "3.9.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v3.9: gercek AudioPlaybackCapture + AAC + MP4 mux')
