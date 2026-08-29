from pathlib import Path
import re
p=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=p.read_text(encoding='utf-8')
start=s.find('    @Suppress("MissingPermission")\n    private fun startDirectBluetoothVosk(')
end=s.find('    private fun handleVoskResult(',start)
if start<0 or end<0: raise SystemExit('v2.9 bluetooth block bulunamadi')
block='''    @Suppress("MissingPermission")
    private fun startDirectBluetoothVosk(model: org.vosk.Model) {
        val am=getSystemService(android.content.Context.AUDIO_SERVICE) as android.media.AudioManager
        am.mode=android.media.AudioManager.MODE_IN_COMMUNICATION
        binding.tvVoice.text="Interkom ses baglantisi kuruluyor..."

        fun beginCapture(attempt: Int=0) {
            if (!voiceWanted || micSource() != "bluetooth") return
            val inputs=am.getDevices(android.media.AudioManager.GET_DEVICES_INPUTS).toList()
            val btInput=inputs.firstOrNull { it.type==android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
                ?: if (android.os.Build.VERSION.SDK_INT >= 31) inputs.firstOrNull { it.type==android.media.AudioDeviceInfo.TYPE_BLE_HEADSET } else null
            if (btInput==null) {
                if(attempt<12) { binding.root.postDelayed({ beginCapture(attempt+1) },300); return }
                binding.tvVoice.text="Interkom mikrofon girisi bulunamadi"
                return
            }
            try {
                val rates=intArrayOf(16000,8000)
                var rec: android.media.AudioRecord?=null
                var chosenRate=16000
                for(rate in rates) {
                    try {
                        val min=android.media.AudioRecord.getMinBufferSize(rate,android.media.AudioFormat.CHANNEL_IN_MONO,android.media.AudioFormat.ENCODING_PCM_16BIT)
                        val candidate=android.media.AudioRecord.Builder()
                            .setAudioSource(android.media.MediaRecorder.AudioSource.VOICE_COMMUNICATION)
                            .setAudioFormat(android.media.AudioFormat.Builder().setEncoding(android.media.AudioFormat.ENCODING_PCM_16BIT).setSampleRate(rate).setChannelMask(android.media.AudioFormat.CHANNEL_IN_MONO).build())
                            .setBufferSizeInBytes(kotlin.math.max(min,4096)*2).build()
                        candidate.setPreferredDevice(btInput)
                        if(candidate.state==android.media.AudioRecord.STATE_INITIALIZED) { rec=candidate; chosenRate=rate; break } else candidate.release()
                    } catch (_: Exception) {}
                }
                val recorder=rec ?: run {
                    if(attempt<12) binding.root.postDelayed({ beginCapture(attempt+1) },300) else binding.tvVoice.text="Interkom ses kaydi acilamadi"
                    return
                }
                recorder.startRecording()
                binding.root.postDelayed({
                    val routed=recorder.routedDevice
                    val isBt=routed?.type==android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO || (android.os.Build.VERSION.SDK_INT>=31 && routed?.type==android.media.AudioDeviceInfo.TYPE_BLE_HEADSET)
                    if(!isBt || recorder.recordingState!=android.media.AudioRecord.RECORDSTATE_RECORDING) {
                        try { recorder.stop() } catch (_: Exception) {}; try { recorder.release() } catch (_: Exception) {}
                        if(attempt<12) { binding.tvVoice.text="Interkom mikrofonu bekleniyor..."; binding.root.postDelayed({ beginCapture(attempt+1) },350) }
                        else binding.tvVoice.text="Interkom mikrofonuna baglanamadi"
                        return@postDelayed
                    }
                    val recognizer=org.vosk.Recognizer(model,chosenRate.toFloat())
                    directAudioRecord=recorder; directRecognizer=recognizer; directAudioRunning=true
                    binding.tvVoice.text="Aktif mikrofon: Bluetooth - ${routed?.productName ?: btInput.productName}"
                    directAudioThread=Thread {
                        val buf=ShortArray(2048)
                        try {
                            while(directAudioRunning) {
                                val n=recorder.read(buf,0,buf.size)
                                if(n>0 && recognizer.acceptWaveForm(buf,n)) runOnUiThread { handleVoskResult(recognizer.result) }
                            }
                        } catch (_: Exception) {} finally {
                            try { recorder.stop() } catch (_: Exception) {}; try { recorder.release() } catch (_: Exception) {}; try { recognizer.close() } catch (_: Exception) {}
                            directAudioRecord=null; directRecognizer=null; directAudioRunning=false
                        }
                    }.apply { name="MotoCam-IntercomMic"; start() }
                },250)
            } catch(e: Exception) { binding.tvVoice.text="Interkom mikrofon hatasi: ${e.message ?: "bilinmeyen"}" }
        }

        if(android.os.Build.VERSION.SDK_INT>=31) {
            val comm=am.availableCommunicationDevices.firstOrNull { it.type==android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO || (android.os.Build.VERSION.SDK_INT>=31 && it.type==android.media.AudioDeviceInfo.TYPE_BLE_HEADSET) }
            if(comm!=null) am.setCommunicationDevice(comm)
            binding.root.postDelayed({ beginCapture() },500)
        } else {
            @Suppress("DEPRECATION") am.startBluetoothSco()
            @Suppress("DEPRECATION") run { am.isBluetoothScoOn=true }
            binding.root.postDelayed({ beginCapture() },900)
        }
    }

'''
s=s[:start]+block+s[end:]
p.write_text(s,encoding='utf-8')
g=Path('motocam/app/build.gradle.kts'); t=g.read_text(encoding='utf-8'); t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 21',t,count=1); t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "3.0.0"',t,count=1); g.write_text(t,encoding='utf-8')
print('MotoCam v3.0 SCO wait + routed input verification')
