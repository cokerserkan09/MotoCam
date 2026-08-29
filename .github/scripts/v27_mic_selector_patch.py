from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
text = kt.read_text(encoding='utf-8')

# Persisted microphone source: phone or bluetooth.
anchor = '    private fun stopCommand(): String = normalizeCommand(commandPrefs.getString("stop_command", "serkan") ?: "serkan")\n'
if anchor not in text:
    raise SystemExit('stopCommand anchor bulunamadi')
extra = '''    private fun micSource(): String = commandPrefs.getString("mic_source", "phone") ?: "phone"\n\n'''
if 'private fun micSource()' not in text:
    text = text.replace(anchor, anchor + extra, 1)

# Replace settings dialog with command + microphone selector UI.
start = text.find('    private fun showCommandSettings() {')
end = text.find('    private fun playRecordingStartedSound()', start)
if start == -1 or end == -1:
    raise SystemExit('showCommandSettings blogu bulunamadi')
settings = '''    private fun showCommandSettings() {
        if (activeRecording != null) { toast("Kayıt sırasında ayarlar değiştirilemez."); return }
        val box = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            val p = (20 * resources.displayMetrics.density).toInt(); setPadding(p, p / 2, p, 0)
        }
        val startInput = android.widget.EditText(this).apply { hint = "Kaydı başlatma kelimesi"; setText(startCommand()); inputType = android.text.InputType.TYPE_CLASS_TEXT }
        val stopInput = android.widget.EditText(this).apply { hint = "Kaydı durdurma kelimesi"; setText(stopCommand()); inputType = android.text.InputType.TYPE_CLASS_TEXT }
        val micTitle = android.widget.TextView(this).apply {
            text = "Mikrofon seçimi"
            textSize = 17f
            setPadding(0, (14 * resources.displayMetrics.density).toInt(), 0, (6 * resources.displayMetrics.density).toInt())
        }
        val micGroup = android.widget.RadioGroup(this).apply { orientation = android.widget.RadioGroup.VERTICAL }
        val phoneMic = android.widget.RadioButton(this).apply { id = android.view.View.generateViewId(); text = "Telefon mikrofonu" }
        val bluetoothMic = android.widget.RadioButton(this).apply { id = android.view.View.generateViewId(); text = "Bluetooth / interkom mikrofonu" }
        micGroup.addView(phoneMic); micGroup.addView(bluetoothMic)
        if (micSource() == "bluetooth") bluetoothMic.isChecked = true else phoneMic.isChecked = true
        box.addView(startInput); box.addView(stopInput); box.addView(micTitle); box.addView(micGroup)
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("MotoCam Ayarları")
            .setMessage("Sesli komutları ve kullanılacak mikrofonu seçin.")
            .setView(box)
            .setPositiveButton("KAYDET") { _, _ ->
                val startWord = normalizeCommand(startInput.text.toString()); val stopWord = normalizeCommand(stopInput.text.toString())
                if (startWord.isBlank() || stopWord.isBlank() || startWord == stopWord || startWord.contains(" ") || stopWord.contains(" ")) {
                    toast("İki farklı, tek kelimelik komut girin.")
                } else {
                    val source = if (bluetoothMic.isChecked) "bluetooth" else "phone"
                    commandPrefs.edit().putString("start_command", startWord).putString("stop_command", stopWord).putString("mic_source", source).apply()
                    stopVoiceControl()
                    binding.root.postDelayed({
                        applySelectedMicRoute()
                        startVoiceControl()
                    }, 250)
                    binding.tvVoice.text = if (source == "bluetooth") "Bluetooth mikrofonu seçildi" else "Telefon mikrofonu seçildi"
                    toast(if (source == "bluetooth") "Bluetooth/interkom mikrofonu seçildi." else "Telefon mikrofonu seçildi.")
                }
            }
            .setNegativeButton("İPTAL", null).show()
    }

'''
text = text[:start] + settings + text[end:]

# Replace bluetooth-only routing with explicit selected routing.
route_start = text.find('    private fun tryRouteBluetoothMic() {')
route_end = text.find('    private fun ', route_start + 10)
if route_start == -1 or route_end == -1:
    raise SystemExit('tryRouteBluetoothMic blogu bulunamadi')
route = '''    private fun applySelectedMicRoute() {
        try {
            val audioManager = getSystemService(android.content.Context.AUDIO_SERVICE) as android.media.AudioManager
            if (micSource() == "phone") {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                    audioManager.clearCommunicationDevice()
                } else {
                    @Suppress("DEPRECATION")
                    audioManager.stopBluetoothSco()
                    @Suppress("DEPRECATION")
                    audioManager.isBluetoothScoOn = false
                }
                audioManager.mode = android.media.AudioManager.MODE_NORMAL
                binding.tvVoice.text = "Telefon mikrofonu aktif"
                return
            }

            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                val granted = androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.BLUETOOTH_CONNECT) == android.content.pm.PackageManager.PERMISSION_GRANTED
                if (!granted) {
                    requestPermissions(arrayOf(android.Manifest.permission.BLUETOOTH_CONNECT), 4243)
                    binding.tvVoice.text = "Bluetooth mikrofon izni bekleniyor"
                    return
                }
                audioManager.mode = android.media.AudioManager.MODE_IN_COMMUNICATION
                val btDevice = audioManager.availableCommunicationDevices.firstOrNull { it.type == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
                if (btDevice != null) {
                    val ok = audioManager.setCommunicationDevice(btDevice)
                    binding.tvVoice.text = if (ok) "Bluetooth mikrofonu aktif" else "Bluetooth mikrofonu bağlanamadı"
                } else {
                    binding.tvVoice.text = "Bluetooth mikrofonu bulunamadı"
                }
            } else {
                @Suppress("DEPRECATION")
                audioManager.mode = android.media.AudioManager.MODE_IN_COMMUNICATION
                @Suppress("DEPRECATION")
                audioManager.startBluetoothSco()
                @Suppress("DEPRECATION")
                audioManager.isBluetoothScoOn = true
                binding.tvVoice.text = "Bluetooth mikrofonu etkinleştiriliyor"
            }
        } catch (_: Exception) {
            binding.tvVoice.text = "Mikrofon yönlendirmesi başarısız"
        }
    }

    private fun tryRouteBluetoothMic() {
        applySelectedMicRoute()
    }

'''
text = text[:route_start] + route + text[route_end:]

# Ensure the selected route is applied before Vosk opens AudioRecord.
text = text.replace('        tryRouteBluetoothMic()\n\n        if (speechService != null)', '        applySelectedMicRoute()\n\n        if (speechService != null)')
text = text.replace('        tryRouteBluetoothMic()\n        binding.root.postDelayed({ tryRouteBluetoothMic() }, 250)\n', '        applySelectedMicRoute()\n        binding.root.postDelayed({ applySelectedMicRoute() }, 250)\n')

kt.write_text(text, encoding='utf-8')

gradle = Path('motocam/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 18', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "2.7.0"', g, count=1)
gradle.write_text(g, encoding='utf-8')

print('MotoCam v2.7: Ayarlara Telefon mikrofonu / Bluetooth mikrofonu secimi eklendi')
