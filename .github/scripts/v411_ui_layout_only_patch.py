from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# UI-only patch: no recording/camera/audio/voice/diagnostics logic is changed.
# Do not assume a generated ViewBinding name for the keep-screen switch: locate it by visible text.
helper=r'''
    private fun findKeepScreenSwitchView(): android.view.View? {
        return try {
            val found = java.util.ArrayList<android.view.View>()
            binding.root.findViewsWithText(found, "ekran", android.view.View.FIND_VIEWS_WITH_TEXT)
            found.firstOrNull { v ->
                v is android.widget.CompoundButton &&
                    ((v.text?.toString()?.lowercase(java.util.Locale.ROOT)?.contains("ekran") == true) ||
                     (v.contentDescription?.toString()?.lowercase(java.util.Locale.ROOT)?.contains("ekran") == true))
            }
        } catch (_: Throwable) { null }
    }
'''
if 'private fun findKeepScreenSwitchView()' not in s:
    anchor='    private fun showFeatureSettings()'
    if anchor not in s: raise SystemExit('Ozellikler fonksiyon anchor bulunamadi')
    s=s.replace(anchor,helper+'\n'+anchor,1)

needle='        applyCameraFeatureMode()'
ui=r'''        // v4.11 UI-only main screen arrangement.
        try {
            // Remove Gallery from the main screen.
            val gallery = try { binding.btnGallery } catch (_: Throwable) { null }
            (gallery?.parent as? android.view.ViewGroup)?.removeView(gallery)

            val voice = binding.switchVoice
            val stabilization = binding.switchStabilization
            val keepScreen = findKeepScreenSwitchView()
            val controlParent = voice.parent as? android.view.ViewGroup

            // Remove available switches from the main screen. Their original View objects,
            // listeners and state remain intact and are shown inside Features when requested.
            listOfNotNull<android.view.View>(voice, stabilization, keepScreen).forEach { v ->
                (v.parent as? android.view.ViewGroup)?.removeView(v)
            }

            // Rebuild only the bottom button row: Settings | Features.
            val settings = settingsButton
            val features = controlParent?.let { p ->
                (0 until p.childCount).map { p.getChildAt(it) }
                    .filterIsInstance<android.widget.Button>()
                    .firstOrNull { it.text?.toString() == "ÖZELLİKLER" }
            }
            (settings.parent as? android.view.ViewGroup)?.removeView(settings)
            (features?.parent as? android.view.ViewGroup)?.removeView(features)
            if (controlParent != null && features != null) {
                val row = android.widget.LinearLayout(this).apply {
                    orientation = android.widget.LinearLayout.HORIZONTAL
                    gravity = android.view.Gravity.CENTER
                }
                val margin=(6 * resources.displayMetrics.density).toInt()
                val slp=android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,1f).apply { setMargins(margin,margin,margin/2,margin) }
                val flp=android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,1f).apply { setMargins(margin/2,margin,margin,margin) }
                row.addView(settings,slp); row.addView(features,flp)
                controlParent.addView(row)
            }

            // Put the status panel beside the Start button when both share a movable parent.
            val start = binding.btnRecord
            val status = binding.tvStatus.parent as? android.view.View
            val startParent = start.parent as? android.view.ViewGroup
            if (status != null && startParent != null && status.parent is android.view.ViewGroup && status !== start) {
                val statusParent=status.parent as android.view.ViewGroup
                // Only move a dedicated status container; never move the root/camera preview container.
                if (statusParent !== binding.root && statusParent.childCount <= 6) {
                    statusParent.removeView(status)
                    startParent.removeView(start)
                    val row=android.widget.LinearLayout(this).apply { orientation=android.widget.LinearLayout.HORIZONTAL; gravity=android.view.Gravity.CENTER_VERTICAL }
                    val m=(6*resources.displayMetrics.density).toInt()
                    row.addView(status,android.widget.LinearLayout.LayoutParams(0,android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,1f).apply{setMargins(m,m,m/2,m)})
                    row.addView(start,android.widget.LinearLayout.LayoutParams(0,android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,1f).apply{setMargins(m/2,m,m,m)})
                    startParent.addView(row,0)
                }
            }
        } catch (t: Throwable) {
            reportMotoCamLogicIssue("v4.11 arayüz yerleşimi uygulanamadı. Mevcut işlevler korunuyor.\n${android.util.Log.getStackTraceString(t)}")
        }
'''
if 'v4.11 UI-only main screen arrangement' not in s:
    if needle not in s: raise SystemExit('UI ekleme noktasi bulunamadi')
    s=s.replace(needle,needle+'\n'+ui,1)

# Extend Features dialog with the existing switches without replacing their listeners.
old='''        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Özellikler")
            .setSingleChoiceItems(modes, current) { dialog, which ->'''
new='''        val featureBox = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            val p=(16*resources.displayMetrics.density).toInt(); setPadding(p,p/2,p,p/2)
        }
        listOfNotNull<android.view.View>(binding.switchVoice, binding.switchStabilization, findKeepScreenSwitchView()).forEach { sw ->
            (sw.parent as? android.view.ViewGroup)?.removeView(sw)
            featureBox.addView(sw)
        }
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Özellikler")
            .setView(featureBox)
            .setSingleChoiceItems(modes, current) { dialog, which ->'''
if old in s:
    s=s.replace(old,new,1)
else:
    raise SystemExit('Ozellikler dialog anchor bulunamadi')

kt.write_text(s,encoding='utf-8')
g=Path('motocam/app/build.gradle.kts'); t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 41',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.11.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v4.11 UI-only: gallery removed; switches moved to Features; Settings+Features side-by-side; status beside Record when safe')
