from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
text=kt.read_text(encoding='utf-8')

# Add direct AudioRecord state. Vosk SpeechService chooses its own input; for Bluetooth
# we instead own AudioRecord and explicitly set the selected SCO input as preferredDevice.
anchor='    private var speechService: org.vosk.android.SpeechService? = null\n'
extra='''    private var directAudioRecord: android.media.AudioRecord? = null
    private var directRecognizer: org.vosk.Recognizer? = null
    @Volatile private var directAudioRunning = false
    private var directAudioThread: Thread? = null
'''
if extra.strip() not in text:
    text=text.replace(anchor,anchor+extra,1)

start=text.find('    private fun startVoskListening() {')
end=text.find('    private fun handleVoskResult(',start)
if start<0 or end<0: raise SystemExit('Vosk listening block bulunamadi')
new='''    private fun startVoskListening() {
        if (!voiceWanted || !binding.switchVoice.isChecked || !hasMicPermission()) return
        val model = voskModel ?: return
        if (speechService != null || directAudioRunning) return

        applySelectedMicRoute()
        if (micSource() == "bluetooth") {
            startDirectBluetoothVosk(model)
            return
        }

        try {
            val recognizer = org.vosk.Recognizer(model, 16000.0f)
            val service = org.vosk.android.SpeechService(recognizer, 16000.0f)
            speechService = service
            binding.tvVoice.text = "Aktif mikrofon: Telefon - dinliyor"
            service.startListening(object : org.vosk.android.RecognitionListener {
                override fun onPartialResult(hypothesis: String?) {}
                override fun onResult(hypothesis: String?) { handleVoskResult(hypothesis) }
                override fun onFinalResult(hypothesis: String?) { handleVoskResult(hypothesis) }
                override fun onError(exception: Exception?) {
                    speechService = null
                    if (voiceWanted && binding.switchVoice.isChecked) binding.root.postDelayed({ startVoskListening() },800)
                }
                override fun onTimeout() {
                    speechService = null
                    if (voiceWanted && binding.switchVoice.isChecked) binding.root.postDelayed({ startVoskListening() },200)
                }
            })
        } catch (e: Exception) {
            speechService=null
            binding.tvVoice.text="Telefon mikrofonu baslatilamadi"
        }
    }

    @Suppress("MissingPermission")
    private fun startDirectBluetoothVosk(model: org.vosk.Model) {
        try {
            val am=getSystemService(android.content.Context.AUDIO_SERVICE) as android.media.AudioManager
            am.mode=android.media.AudioManager.MODE_IN_COMMUNICATION
            var btInput: android.media.AudioDeviceInfo?=null
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                btInput=am.availableCommunicationDevices.firstOrNull { it.type==android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
                if (btInput!=null) am.setCommunicationDevice(btInput)
            } else {
                @Suppress("DEPRECATION") am.startBluetoothSco()
                @Suppress("DEPRECATION") run { am.isBluetoothScoOn=true }
                btInput=am.getDevices(android.media.AudioManager.GET_DEVICES_INPUTS).firstOrNull { it.type==android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
            }
            if (btInput==null) {
                binding.tvVoice.text="Interkom mikrofon girisi bulunamadi"
                return
            }
            val rate=16000
            val min=android.media.AudioRecord.getMinBufferSize(rate,android.media.AudioFormat.CHANNEL_IN_MONO,android.media.AudioFormat.ENCODING_PCM_16BIT)
            val rec=android.media.AudioRecord.Builder()
                .setAudioSource(android.media.MediaRecorder.AudioSource.VOICE_RECOGNITION)
                .setAudioFormat(android.media.AudioFormat.Builder().setEncoding(android.media.AudioFormat.ENCODING_PCM_16BIT).setSampleRate(rate).setChannelMask(android.media.AudioFormat.CHANNEL_IN_MONO).build())
                .setBufferSizeInBytes(kotlin.math.max(min,4096)*2)
                .build()
            val preferred=rec.setPreferredDevice(btInput)
            if (!preferred) {
                rec.release()
                binding.tvVoice.text="Interkom mikrofonuna baglanamadi"
                return
            }
            val recognizer=org.vosk.Recognizer(model,rate.toFloat())
            directAudioRecord=rec; directRecognizer=recognizer; directAudioRunning=true
            rec.startRecording()
            val dev=rec.routedDevice
            val devName=dev?.productName?.toString() ?: btInput.productName?.toString() ?: "interkom"
            binding.tvVoice.text="Aktif mikrofon: Bluetooth - $devName"
            directAudioThread=Thread {
                val buf=ShortArray(2048)
                try {
                    while(directAudioRunning) {
                        val n=rec.read(buf,0,buf.size)
                        if(n>0 && recognizer.acceptWaveForm(buf,n)) {
                            val result=recognizer.result
                            runOnUiThread { handleVoskResult(result) }
                        }
                    }
                    val result=recognizer.finalResult
                    runOnUiThread { handleVoskResult(result) }
                } catch (_: Exception) {} finally {
                    try { rec.stop() } catch (_: Exception) {}
                    try { rec.release() } catch (_: Exception) {}
                    try { recognizer.close() } catch (_: Exception) {}
                    directAudioRecord=null; directRecognizer=null; directAudioRunning=false
                }
            }.apply { name="MotoCam-BluetoothMic"; start() }
        } catch (e: Exception) {
            directAudioRunning=false
            binding.tvVoice.text="Interkom mikrofon hatasi: ${e.message ?: "bilinmeyen"}"
        }
    }

'''
text=text[:start]+new+text[end:]

# Extend stopVoiceControl to stop our owned recorder too.
old='''    private fun stopVoiceControl() {
        try { speechService?.stop() } catch (_: Exception) {}
        try { speechService?.shutdown() } catch (_: Exception) {}
        speechService = null
    }'''
newstop='''    private fun stopVoiceControl() {
        try { speechService?.stop() } catch (_: Exception) {}
        try { speechService?.shutdown() } catch (_: Exception) {}
        speechService = null
        directAudioRunning = false
        try { directAudioRecord?.stop() } catch (_: Exception) {}
        directAudioThread = null
    }'''
if old not in text: raise SystemExit('stopVoiceControl bulunamadi')
text=text.replace(old,newstop,1)

kt.write_text(text,encoding='utf-8')
gradle=Path('motocam/app/build.gradle.kts'); g=gradle.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s*=\s*\d+','versionCode = 20',g,count=1)
g=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "2.9.0"',g,count=1)
gradle.write_text(g,encoding='utf-8')
print('MotoCam v2.9 direct Bluetooth AudioRecord + preferredDevice')
