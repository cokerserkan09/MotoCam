from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
text = kt.read_text(encoding='utf-8')

start = text.find('    private fun tryRouteBluetoothMic() {')
if start == -1:
    raise SystemExit('tryRouteBluetoothMic bulunamadi')
end = text.find('    private fun ', start + 10)
if end == -1:
    raise SystemExit('tryRouteBluetoothMic sonu bulunamadi')

replacement = '''    private fun tryRouteBluetoothMic() {
        try {
            val audioManager = getSystemService(android.content.Context.AUDIO_SERVICE) as android.media.AudioManager

            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                val granted = androidx.core.content.ContextCompat.checkSelfPermission(
                    this,
                    android.Manifest.permission.BLUETOOTH_CONNECT
                ) == android.content.pm.PackageManager.PERMISSION_GRANTED

                if (!granted) {
                    requestPermissions(arrayOf(android.Manifest.permission.BLUETOOTH_CONNECT), 4243)
                    binding.tvVoice.text = "İnterkom mikrofon izni bekleniyor"
                    return
                }

                audioManager.mode = android.media.AudioManager.MODE_IN_COMMUNICATION
                val btDevice = audioManager.availableCommunicationDevices.firstOrNull {
                    it.type == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO
                }
                if (btDevice != null) {
                    val ok = audioManager.setCommunicationDevice(btDevice)
                    binding.tvVoice.text = if (ok) "İnterkom mikrofonu aktif" else "İnterkom mikrofonu bağlanamadı"
                } else {
                    binding.tvVoice.text = "İnterkom mikrofonu bulunamadı"
                }
            } else {
                @Suppress("DEPRECATION")
                audioManager.mode = android.media.AudioManager.MODE_IN_COMMUNICATION
                @Suppress("DEPRECATION")
                audioManager.startBluetoothSco()
                @Suppress("DEPRECATION")
                audioManager.isBluetoothScoOn = true
                binding.tvVoice.text = "İnterkom mikrofonu etkinleştiriliyor"
            }
        } catch (e: Exception) {
            binding.tvVoice.text = "İnterkom mikrofon yönlendirmesi başarısız"
        }
    }

'''
text = text[:start] + replacement + text[end:]

# Re-route shortly before Vosk starts; SCO/HFP may need a moment to become active.
needle = '    private fun startVoskListening() {\n'
if needle in text and 'binding.root.postDelayed({ tryRouteBluetoothMic() }, 250)' not in text:
    text = text.replace(needle, needle + '        tryRouteBluetoothMic()\n        binding.root.postDelayed({ tryRouteBluetoothMic() }, 250)\n', 1)

kt.write_text(text, encoding='utf-8')

manifest = Path('motocam/app/src/main/AndroidManifest.xml')
m = manifest.read_text(encoding='utf-8')
perm = '    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />\n'
if 'android.permission.BLUETOOTH_CONNECT' not in m:
    anchor = '<manifest'
    pos = m.find('>')
    if pos == -1:
        raise SystemExit('manifest acilisi bulunamadi')
    m = m[:pos+1] + '\n' + perm + m[pos+1:]
manifest.write_text(m, encoding='utf-8')

gradle = Path('motocam/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 17', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.6.0"', g, count=1)
gradle.write_text(g, encoding='utf-8')

print('MotoCam v2.6: Android 12+ communication device / eski Android SCO interkom mikrofon yonlendirmesi uygulandi')
