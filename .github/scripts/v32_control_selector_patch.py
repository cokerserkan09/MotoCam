from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# mic_source artik kontrol yontemini de tutar: phone, bluetooth, jack35, typec.
# Ayarlar ekranini 4 kontrol secenekli hale getir.
start=s.find('    private fun showCommandSettings() {')
end=s.find('    private fun playRecordingStartedSound()', start)
if start<0 or end<0: raise SystemExit('showCommandSettings bulunamadi')
settings='''    private fun showCommandSettings() {
        if (activeRecording != null) { toast("Kayıt sırasında ayarlar değiştirilemez."); return }
        val box = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            val p = (20 * resources.displayMetrics.density).toInt(); setPadding(p, p / 2, p, 0)
        }
        val startInput = android.widget.EditText(this).apply { hint = "Kaydı başlatma kelimesi"; setText(startCommand()); inputType = android.text.InputType.TYPE_CLASS_TEXT }
        val stopInput = android.widget.EditText(this).apply { hint = "Kaydı durdurma kelimesi"; setText(stopCommand()); inputType = android.text.InputType.TYPE_CLASS_TEXT }
        val controlTitle = android.widget.TextView(this).apply {
            text = "Kontrol yöntemi"
            textSize = 17f
            setPadding(0, (14 * resources.displayMetrics.density).toInt(), 0, (6 * resources.displayMetrics.density).toInt())
        }
        val group = android.widget.RadioGroup(this).apply { orientation = android.widget.RadioGroup.VERTICAL }
        val phone = android.widget.RadioButton(this).apply { id = android.view.View.generateViewId(); text = "Sesli komut - Telefon mikrofonu" }
        val bluetooth = android.widget.RadioButton(this).apply { id = android.view.View.generateViewId(); text = "Sesli komut - Bluetooth / interkom" }
        val jack35 = android.widget.RadioButton(this).apply { id = android.view.View.generateViewId(); text = "3,5 mm kulaklık jakı tuşu" }
        val typec = android.widget.RadioButton(this).apply { id = android.view.View.generateViewId(); text = "Type-C kablolu tuş" }
        group.addView(phone); group.addView(bluetooth); group.addView(jack35); group.addView(typec)
        when (micSource()) {
            "bluetooth" -> bluetooth.isChecked = true
            "jack35" -> jack35.isChecked = true
            "typec" -> typec.isChecked = true
            else -> phone.isChecked = true
        }
        box.addView(startInput); box.addView(stopInput); box.addView(controlTitle); box.addView(group)
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("MotoCam Ayarları")
            .setMessage("Kaydı nasıl başlatıp durduracağınızı seçin. Kablolu tuş modlarında aynı tuşa bir kez basmak kaydı başlatır, tekrar basmak durdurur.")
            .setView(box)
            .setPositiveButton("KAYDET") { _, _ ->
                val startWord = normalizeCommand(startInput.text.toString())
                val stopWord = normalizeCommand(stopInput.text.toString())
                if (startWord.isBlank() || stopWord.isBlank() || startWord == stopWord || startWord.contains(" ") || stopWord.contains(" ")) {
                    toast("İki farklı, tek kelimelik komut girin.")
                } else {
                    val mode = when {
                        bluetooth.isChecked -> "bluetooth"
                        jack35.isChecked -> "jack35"
                        typec.isChecked -> "typec"
                        else -> "phone"
                    }
                    commandPrefs.edit().putString("start_command", startWord).putString("stop_command", stopWord).putString("mic_source", mode).apply()
                    stopVoiceControl()
                    applySelectedMicRoute()
                    if (mode == "phone" || mode == "bluetooth") {
                        binding.root.postDelayed({ startVoiceControl() }, 250)
                    }
                    binding.tvVoice.text = when(mode) {
                        "bluetooth" -> "Kontrol: Sesli komut / Bluetooth"
                        "jack35" -> "Kontrol: 3,5 mm kablolu tuş"
                        "typec" -> "Kontrol: Type-C kablolu tuş"
                        else -> "Kontrol: Sesli komut / Telefon"
                    }
                    toast(binding.tvVoice.text.toString())
                }
            }
            .setNegativeButton("İPTAL", null).show()
    }

'''
s=s[:start]+settings+s[end:]

# Kablolu modda Bluetooth ses rotasi acmaya calisma.
s=s.replace('if (micSource() == "phone") {','if (micSource() != "bluetooth") {',1)

# Vosk sadece iki sesli kontrol modunda calissin.
needle='''    private fun startVoskListening() {
        if (!voiceWanted || !binding.switchVoice.isChecked || !hasMicPermission()) return
        val model = voskModel ?: return
'''
repl='''    private fun startVoskListening() {
        if (!voiceWanted || !binding.switchVoice.isChecked || !hasMicPermission()) return
        val selectedControl = micSource()
        if (selectedControl == "jack35" || selectedControl == "typec") {
            binding.tvVoice.text = if (selectedControl == "jack35") "Kontrol: 3,5 mm kablolu tuş" else "Kontrol: Type-C kablolu tuş"
            return
        }
        val model = voskModel ?: return
'''
if needle not in s: raise SystemExit('startVoskListening anchor bulunamadi')
s=s.replace(needle,repl,1)

# Fiziksel kulaklik / USB-C medya tuslarini tek tus toggle olarak yakala.
insert_at=s.find('    private fun showCommandSettings() {')
keyblock='''    private var lastWiredButtonMs = 0L

    override fun dispatchKeyEvent(event: android.view.KeyEvent): Boolean {
        val mode = micSource()
        if ((mode == "jack35" || mode == "typec") && event.action == android.view.KeyEvent.ACTION_DOWN && event.repeatCount == 0) {
            val key = event.keyCode
            val analogKeys = setOf(
                android.view.KeyEvent.KEYCODE_HEADSETHOOK,
                android.view.KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE,
                android.view.KeyEvent.KEYCODE_MEDIA_PLAY,
                android.view.KeyEvent.KEYCODE_MEDIA_PAUSE,
                android.view.KeyEvent.KEYCODE_CAMERA,
                android.view.KeyEvent.KEYCODE_VOLUME_UP,
                android.view.KeyEvent.KEYCODE_VOLUME_DOWN
            )
            val usbExtra = setOf(
                android.view.KeyEvent.KEYCODE_ENTER,
                android.view.KeyEvent.KEYCODE_SPACE,
                android.view.KeyEvent.KEYCODE_DPAD_CENTER
            )
            val accepted = analogKeys.contains(key) || (mode == "typec" && usbExtra.contains(key))
            if (accepted) {
                val now = android.os.SystemClock.elapsedRealtime()
                if (now - lastWiredButtonMs > 650L) {
                    lastWiredButtonMs = now
                    if (activeRecording == null) {
                        startRecording()
                        binding.tvVoice.text = if (mode == "jack35") "3,5 mm tuş: KAYIT BAŞLADI" else "Type-C tuş: KAYIT BAŞLADI"
                    } else {
                        voiceStopRequested = false
                        stopRecording()
                        binding.tvVoice.text = if (mode == "jack35") "3,5 mm tuş: KAYIT DURDU" else "Type-C tuş: KAYIT DURDU"
                        binding.root.postDelayed({ playRecordingStoppedSound() }, 350)
                    }
                }
                return true
            }
        }
        return super.dispatchKeyEvent(event)
    }

'''
if 'override fun dispatchKeyEvent' not in s:
    s=s[:insert_at]+keyblock+s[insert_at:]

kt.write_text(s,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 23',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "3.2.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v3.2: 4 kontrol modu + 3.5mm/Type-C tek tus toggle')
