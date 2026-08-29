from pathlib import Path
import re
p=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=p.read_text(encoding='utf-8')

# Add a lightweight handler for live Vosk partials. In continuous road noise Vosk may
# never emit a final sentence, so command words must be accepted from partial results.
anchor='    private fun handleVoskResult('
pos=s.find(anchor)
if pos<0: raise SystemExit('handleVoskResult bulunamadi')
helper='''    private fun handleLiveVoskPartial(hypothesis: String?) {
        if (hypothesis.isNullOrBlank()) return
        try {
            val obj = org.json.JSONObject(hypothesis)
            val partial = normalizeCommand(obj.optString("partial", ""))
            if (partial.isBlank()) return
            val clean = partial.replace(Regex("[^a-zçğıöşü ]"), " ").trim()
            val words = clean.split(Regex("\\s+")).filter { it.isNotBlank() }
            val startWord = startCommand()
            val stopWord = stopCommand()
            val last = words.lastOrNull() ?: return
            val now = android.os.SystemClock.elapsedRealtime()
            if (now - lastVoiceCommandMs < 1200L) return
            when {
                last == stopWord -> {
                    lastVoiceCommandMs = now
                    runOnUiThread {
                        binding.tvVoice.text = "Duyuldu: $stopWord"
                        voiceStopRequested = true
                        stopRecording()
                    }
                }
                last == startWord && activeRecording == null -> {
                    lastVoiceCommandMs = now
                    runOnUiThread {
                        binding.tvVoice.text = "Duyuldu: $startWord"
                        startRecording()
                    }
                }
            }
        } catch (_: Exception) {}
    }

'''
if 'private fun handleLiveVoskPartial' not in s:
    s=s[:pos]+helper+s[pos:]

# In the direct Bluetooth AudioRecord loop, inspect partial recognition continuously.
old='''                                val n=recorder.read(buf,0,buf.size)
                                if(n>0 && recognizer.acceptWaveForm(buf,n)) runOnUiThread { handleVoskResult(recognizer.result) }'''
new='''                                val n=recorder.read(buf,0,buf.size)
                                if(n>0) {
                                    var sum=0.0
                                    for(i in 0 until n) { val v=buf[i].toDouble(); sum += v*v }
                                    val rms=kotlin.math.sqrt(sum / kotlin.math.max(1,n))
                                    if(recognizer.acceptWaveForm(buf,n)) {
                                        runOnUiThread { handleVoskResult(recognizer.result) }
                                    } else {
                                        val partial=recognizer.partialResult
                                        handleLiveVoskPartial(partial)
                                        if(rms > 250.0) runOnUiThread {
                                            val bars=kotlin.math.min(10, kotlin.math.max(1,(rms/1200.0).toInt()+1))
                                            binding.tvVoice.text="Interkom dinliyor " + "|".repeat(bars)
                                        }
                                    }
                                }'''
if old not in s: raise SystemExit('v3.0 direct loop bulunamadi')
s=s.replace(old,new,1)

# Phone-mic Vosk also gets safe exact-word partial handling; this improves road-noise endpointing.
s=s.replace('''                override fun onPartialResult(hypothesis: String?) {}''','''                override fun onPartialResult(hypothesis: String?) { handleLiveVoskPartial(hypothesis) }''',1)

p.write_text(s,encoding='utf-8')
g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 22',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "3.1.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v3.1 live partial command recognition + intercom level meter')
