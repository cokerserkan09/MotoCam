from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')

# --- Phone-call pause/resume state ---
anchor = '    private fun videoAudioSource(): String = commandPrefs.getString("video_audio_source", "mic") ?: "mic"\n'
if anchor not in s:
    raise SystemExit('v3.4 videoAudioSource anchor bulunamadi')
helpers = '''    private val phoneStatePermissionRequestCode = 7352
    private var phoneCallPausedRecording = false
    private var phoneTelephonyCallback: android.telephony.TelephonyCallback? = null
    private var legacyPhoneStateListener: android.telephony.PhoneStateListener? = null
    private var segmentPausedRemainingMs: Long? = null
    private var segmentTimerStartedElapsedMs: Long = 0L
    private var segmentTimerScheduledMs: Long = 0L

    private fun pauseSegmentTimerForPhoneCall() {
        if (!segmentSequenceActive || segmentStopRunnable == null) return
        val elapsed = (android.os.SystemClock.elapsedRealtime() - segmentTimerStartedElapsedMs).coerceAtLeast(0L)
        segmentPausedRemainingMs = (segmentTimerScheduledMs - elapsed).coerceAtLeast(250L)
        segmentStopRunnable?.let { binding.root.removeCallbacks(it) }
        segmentStopRunnable = null
    }

    private fun resumeSegmentTimerAfterPhoneCall() {
        if (segmentSequenceActive && segmentPausedRemainingMs != null) scheduleSegmentStopIfNeeded()
    }

    private fun handlePhoneCallState(state: Int) {
        runOnUiThread {
            when (state) {
                android.telephony.TelephonyManager.CALL_STATE_RINGING,
                android.telephony.TelephonyManager.CALL_STATE_OFFHOOK -> {
                    if (activeRecording != null && !phoneCallPausedRecording) {
                        try {
                            activeRecording?.pause()
                            phoneCallPausedRecording = true
                            pauseSegmentTimerForPhoneCall()
                            // Release voice-recognition microphone while the phone call owns audio routing.
                            stopVoiceControl()
                            binding.tvStatus.text = "TELEFON ARAMASI • KAYIT BEKLEMEDE"
                            binding.tvVoice.text = "Görüşme bitince kayıt otomatik devam edecek"
                        } catch (_: Exception) {}
                    }
                }
                android.telephony.TelephonyManager.CALL_STATE_IDLE -> {
                    if (phoneCallPausedRecording && activeRecording != null) {
                        try {
                            activeRecording?.resume()
                            phoneCallPausedRecording = false
                            resumeSegmentTimerAfterPhoneCall()
                            binding.tvStatus.text = "● KAYIT"
                            binding.tvVoice.text = "Telefon görüşmesi bitti • kayıt devam ediyor"
                            val mode = micSource()
                            if (mode == "phone" || mode == "bluetooth") {
                                binding.root.postDelayed({
                                    applySelectedMicRoute()
                                    startVoiceControl()
                                }, 700)
                            }
                        } catch (_: Exception) {}
                    } else {
                        phoneCallPausedRecording = false
                    }
                }
            }
        }
    }

    private fun setupPhoneCallPause() {
        if (androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.READ_PHONE_STATE) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            androidx.core.app.ActivityCompat.requestPermissions(this, arrayOf(android.Manifest.permission.READ_PHONE_STATE), phoneStatePermissionRequestCode)
            return
        }
        val tm = getSystemService(android.content.Context.TELEPHONY_SERVICE) as android.telephony.TelephonyManager
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            if (phoneTelephonyCallback != null) return
            val cb = object : android.telephony.TelephonyCallback(), android.telephony.TelephonyCallback.CallStateListener {
                override fun onCallStateChanged(state: Int) { handlePhoneCallState(state) }
            }
            phoneTelephonyCallback = cb
            tm.registerTelephonyCallback(mainExecutor, cb)
        } else {
            if (legacyPhoneStateListener != null) return
            @Suppress("DEPRECATION")
            val listener = object : android.telephony.PhoneStateListener() {
                @Deprecated("Deprecated in Java")
                override fun onCallStateChanged(state: Int, phoneNumber: String?) {
                    handlePhoneCallState(state)
                }
            }
            legacyPhoneStateListener = listener
            @Suppress("DEPRECATION")
            tm.listen(listener, android.telephony.PhoneStateListener.LISTEN_CALL_STATE)
        }
    }

    private fun unregisterPhoneCallPause() {
        val tm = getSystemService(android.content.Context.TELEPHONY_SERVICE) as android.telephony.TelephonyManager
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            phoneTelephonyCallback?.let { try { tm.unregisterTelephonyCallback(it) } catch (_: Exception) {} }
            phoneTelephonyCallback = null
        } else {
            legacyPhoneStateListener?.let {
                @Suppress("DEPRECATION")
                try { tm.listen(it, android.telephony.PhoneStateListener.LISTEN_NONE) } catch (_: Exception) {}
            }
            legacyPhoneStateListener = null
        }
    }

'''
if 'private fun setupPhoneCallPause()' not in s:
    s = s.replace(anchor, anchor + helpers, 1)

# Make segmented recording timer use remaining time after a call pause.
old_duration = '        val durationMs = segmentMinutes().toLong() * 60_000L\n'
new_duration = '''        val durationMs = segmentPausedRemainingMs ?: (segmentMinutes().toLong() * 60_000L)
        segmentPausedRemainingMs = null
        segmentTimerStartedElapsedMs = android.os.SystemClock.elapsedRealtime()
        segmentTimerScheduledMs = durationMs
'''
if old_duration not in s:
    raise SystemExit('segment duration anchor bulunamadi')
s = s.replace(old_duration, new_duration, 1)

# Start phone-state monitoring when UI is ready.
oncreate_anchor = '        setContentView(binding.root)\n'
if oncreate_anchor not in s:
    raise SystemExit('setContentView anchor bulunamadi')
if 'setupPhoneCallPause()' not in s[s.find(oncreate_anchor):s.find(oncreate_anchor)+300]:
    s = s.replace(oncreate_anchor, oncreate_anchor + '        setupPhoneCallPause()\n', 1)

# Permission callback: activate monitoring immediately after user grants Phone permission.
on_destroy = s.find('    override fun onDestroy()')
if on_destroy < 0:
    raise SystemExit('onDestroy bulunamadi')
perm_callback = '''    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == phoneStatePermissionRequestCode && grantResults.isNotEmpty() && grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            setupPhoneCallPause()
            toast("Telefon aramalarında otomatik kayıt bekletme aktif.")
        }
    }

'''
if 'requestCode == phoneStatePermissionRequestCode' not in s:
    s = s[:on_destroy] + perm_callback + s[on_destroy:]

# Unregister listener before Activity is destroyed.
destroy_start = s.find('    override fun onDestroy()')
brace = s.find('{', destroy_start)
if destroy_start < 0 or brace < 0:
    raise SystemExit('onDestroy block bulunamadi')
if 'unregisterPhoneCallPause()' not in s[brace:brace+250]:
    s = s[:brace+1] + '\n        unregisterPhoneCallPause()' + s[brace+1:]

# If user manually stops while a call is active, do not auto-resume afterward.
stop_marker = '    private fun stopRecording() {\n'
if stop_marker not in s:
    raise SystemExit('stopRecording bulunamadi')
if 'phoneCallPausedRecording = false' not in s[s.find(stop_marker):s.find(stop_marker)+250]:
    s = s.replace(stop_marker, stop_marker + '        phoneCallPausedRecording = false\n        segmentPausedRemainingMs = null\n', 1)

# Manifest phone-state permission.
manifest = Path('motocam/app/src/main/AndroidManifest.xml')
m = manifest.read_text(encoding='utf-8')
perm = '    <uses-permission android:name="android.permission.READ_PHONE_STATE" />\n'
if 'android.permission.READ_PHONE_STATE' not in m:
    idx = m.find('<application')
    m = m[:idx] + perm + m[idx:]
manifest.write_text(m, encoding='utf-8')

kt.write_text(s, encoding='utf-8')

gradle = Path('motocam/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 26', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "3.5.0"', g, count=1)
gradle.write_text(g, encoding='utf-8')

print('MotoCam v3.5: telefon aramasinda pause/resume + parca suresi korunuyor')
