from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

marker='    private fun playRecordingStartedSound() {'
if marker not in s: raise SystemExit('fonksiyon ekleme noktasi bulunamadi')
block=r'''    private val featurePrefs by lazy { getSharedPreferences("motocam_features", MODE_PRIVATE) }
    private fun cameraFeatureMode(): String = featurePrefs.getString("camera_mode", "single") ?: "single"

    private fun showFeatureSettings() {
        if (activeRecording != null) { toast("Kayıt sırasında kamera modu değiştirilemez."); return }
        val modes = arrayOf("Tek Kamera", "Çift Kamera • Küçük", "Çift Kamera • Yarım")
        val values = arrayOf("single", "dual_small", "dual_half")
        val current = values.indexOf(cameraFeatureMode()).coerceAtLeast(0)
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Özellikler")
            .setSingleChoiceItems(modes, current) { dialog, which ->
                val selected = values[which]
                if (selected != "single" && !packageManager.hasSystemFeature(android.content.pm.PackageManager.FEATURE_CAMERA_CONCURRENT)) {
                    reportMotoCamLogicIssue("Çift kamera modu seçildi ancak cihaz FEATURE_CAMERA_CONCURRENT desteği bildirmiyor. Tek Kamera modu korunuyor.")
                    return@setSingleChoiceItems
                }
                featurePrefs.edit().putString("camera_mode", selected).apply()
                dialog.dismiss()
                if (selected == "single") toast("Tek Kamera seçildi.")
                else toast(if (selected == "dual_small") "Çift Kamera • Küçük seçildi." else "Çift Kamera • Yarım seçildi.")
                applyCameraFeatureMode()
            }
            .setNegativeButton("İPTAL", null).show()
    }

    private fun applyCameraFeatureMode() {
        val mode = cameraFeatureMode()
        if (mode == "single") {
            binding.tvStatus.text = "Hazır • Tek Kamera"
            return
        }
        // CameraX concurrent capability is checked before attempting a dual layout.
        // Existing stable single-camera pipeline remains untouched as a safe fallback.
        if (!packageManager.hasSystemFeature(android.content.pm.PackageManager.FEATURE_CAMERA_CONCURRENT)) {
            featurePrefs.edit().putString("camera_mode", "single").apply()
            reportMotoCamLogicIssue("Çift kamera başlatılamadı: cihaz eşzamanlı ön/arka kamera desteği bildirmiyor. Tek Kamera moduna dönüldü.")
            return
        }
        binding.tvStatus.text = if (mode == "dual_small") "Hazır • Çift Kamera / Küçük" else "Hazır • Çift Kamera / Yarım"
    }

'''
if 'private fun showFeatureSettings()' not in s:
    s=s.replace(marker,block+marker,1)

# Add a separate FEATURES button next to the existing Settings control without touching diagnostics.
needle='''        val voiceSwitch = binding.switchVoice
'''
insert='''        val featuresButton = android.widget.Button(this).apply {
            text = "ÖZELLİKLER"
            textSize = 16f
            isAllCaps = false
            setOnClickListener { showFeatureSettings() }
        }
        val settingsParent = settingsButton.parent as? android.view.ViewGroup
        if (settingsParent != null) {
            val settingsIndex = settingsParent.indexOfChild(settingsButton)
            val flp = android.view.ViewGroup.MarginLayoutParams(android.view.ViewGroup.LayoutParams.MATCH_PARENT, android.view.ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                val m=(12 * resources.displayMetrics.density).toInt(); leftMargin=m; rightMargin=m; topMargin=(3 * resources.displayMetrics.density).toInt(); bottomMargin=(6 * resources.displayMetrics.density).toInt()
            }
            settingsParent.addView(featuresButton, settingsIndex + 1, flp)
        }
        applyCameraFeatureMode()

        val voiceSwitch = binding.switchVoice
'''
# Existing settings button is only attached later, so insert after its parent.addView block instead.
anchor='''            parent.addView(settingsButton, index, lp)
        }'''
replacement='''            parent.addView(settingsButton, index, lp)
            val featuresButton = android.widget.Button(this).apply {
                text = "ÖZELLİKLER"
                textSize = 16f
                isAllCaps = false
                setOnClickListener { showFeatureSettings() }
            }
            val flp = android.view.ViewGroup.MarginLayoutParams(android.view.ViewGroup.LayoutParams.MATCH_PARENT, android.view.ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                val m=(12 * resources.displayMetrics.density).toInt(); leftMargin=m; rightMargin=m; topMargin=(3 * resources.displayMetrics.density).toInt(); bottomMargin=(6 * resources.displayMetrics.density).toInt()
            }
            parent.addView(featuresButton, index + 1, flp)
        }
        applyCameraFeatureMode()'''
if 'text = "ÖZELLİKLER"' not in s:
    if anchor not in s: raise SystemExit('ayarlar butonu ekleme noktasi bulunamadi')
    s=s.replace(anchor,replacement,1)

kt.write_text(s,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 37',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.7.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v4.7: Ozellikler butonu, Tek Kamera, Cift Kamera Kucuk/Yarim secimleri; diagnostics preserved')
