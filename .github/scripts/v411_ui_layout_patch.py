from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# Extend Features dialog with the three existing main-screen toggles without changing their listeners/logic.
old='''        val modes = arrayOf("Tek Kamera", "Çift Kamera • Küçük", "Çift Kamera • Yarım")
        val values = arrayOf("single", "dual_small", "dual_half")'''
new='''        val modes = arrayOf("Tek Kamera", "Çift Kamera • Küçük", "Çift Kamera • Yarım")
        val values = arrayOf("single", "dual_small", "dual_half")'''
# Keep existing camera chooser intact; toggles are moved visually into a compact Features panel below it.

# Replace the dynamically inserted Settings/Features layout after both buttons already exist.
anchor='''        applyCameraFeatureMode()'''
ui=r'''        applyCameraFeatureMode()

        // v4.11: UI-only rearrangement. Existing feature listeners and recording logic stay untouched.
        binding.btnGallery.visibility = android.view.View.GONE

        val mainParent = binding.switchVoice.parent as? android.widget.LinearLayout
        if (mainParent != null) {
            val switches = listOf<android.view.View>(binding.switchVoice, binding.switchStabilization, binding.switchKeepScreenOn)
            switches.forEach { mainParent.removeView(it) }

            val settings = (0 until mainParent.childCount).map { mainParent.getChildAt(it) }
                .firstOrNull { it is android.widget.Button && it.text.toString().contains("AYARLAR") } as? android.widget.Button
            val features = (0 until mainParent.childCount).map { mainParent.getChildAt(it) }
                .firstOrNull { it is android.widget.Button && it.text.toString().contains("ÖZELLİKLER") } as? android.widget.Button

            if (settings != null && features != null) {
                mainParent.removeView(settings); mainParent.removeView(features)
                val bottomRow = android.widget.LinearLayout(this).apply {
                    orientation = android.widget.LinearLayout.HORIZONTAL
                    gravity = android.view.Gravity.CENTER
                    val p=(8*resources.displayMetrics.density).toInt(); setPadding(p,p/2,p,p)
                }
                val each = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    val m=(4*resources.displayMetrics.density).toInt(); setMargins(m,m,m,m)
                }
                bottomRow.addView(settings, each)
                bottomRow.addView(features, android.widget.LinearLayout.LayoutParams(each))
                mainParent.addView(bottomRow)
            }
        }
'''
if '// v4.11: UI-only rearrangement' not in s:
    pos=s.rfind(anchor)
    if pos<0: raise SystemExit('applyCameraFeatureMode anchor yok')
    s=s[:pos]+s[pos:].replace(anchor,ui,1)

# Feature dialog: add the existing three switches as controls by temporarily hosting them in the dialog,
# then return them to a hidden holder when dialog closes. Listeners remain the original listeners.
start=s.find('    private fun showFeatureSettings() {')
end=s.find('    private fun applyCameraFeatureMode()',start)
if start<0 or end<0: raise SystemExit('showFeatureSettings yok')
oldfun=s[start:end]
newfun=r'''    private fun showFeatureSettings() {
        if (activeRecording != null) { toast("Kayıt sırasında kamera modu değiştirilemez."); return }
        val box = android.widget.LinearLayout(this).apply {
            orientation=android.widget.LinearLayout.VERTICAL
            val p=(18*resources.displayMetrics.density).toInt(); setPadding(p,p/2,p,p/2)
        }
        val modes=arrayOf("Tek Kamera","Çift Kamera • Küçük","Çift Kamera • Yarım")
        val values=arrayOf("single","dual_small","dual_half")
        val current=values.indexOf(cameraFeatureMode()).coerceAtLeast(0)
        val cameraTitle=android.widget.TextView(this).apply { text="Kamera modu"; textSize=17f; setPadding(0,8,0,4) }
        box.addView(cameraTitle)
        val group=android.widget.RadioGroup(this).apply { orientation=android.widget.RadioGroup.VERTICAL }
        modes.forEachIndexed { i,label ->
            val rb=android.widget.RadioButton(this).apply { text=label; id=10040+i; isChecked=i==current }
            group.addView(rb)
        }
        box.addView(group)
        val divider=android.view.View(this).apply { setBackgroundColor(0x44777777) }
        box.addView(divider,android.widget.LinearLayout.LayoutParams(android.widget.LinearLayout.LayoutParams.MATCH_PARENT,(1*resources.displayMetrics.density).toInt()).apply{topMargin=(10*resources.displayMetrics.density).toInt();bottomMargin=(8*resources.displayMetrics.density).toInt()})
        val featureTitle=android.widget.TextView(this).apply { text="Kayıt özellikleri"; textSize=17f }
        box.addView(featureTitle)
        fun addToggle(label:String, source:android.widget.CompoundButton) {
            val sw=androidx.appcompat.widget.SwitchCompat(this).apply {
                text=label; textSize=16f; isChecked=source.isChecked
                setOnCheckedChangeListener { _,checked -> if(source.isChecked!=checked) source.isChecked=checked }
            }
            source.setOnCheckedChangeListener(source.getTag(0x7f0a0f01) as? android.widget.CompoundButton.OnCheckedChangeListener)
            box.addView(sw,android.widget.LinearLayout.LayoutParams(android.widget.LinearLayout.LayoutParams.MATCH_PARENT,android.widget.LinearLayout.LayoutParams.WRAP_CONTENT))
        }
        // Mirror state through performClick so the original app listeners execute unchanged.
        fun addMirror(label:String, source:android.widget.CompoundButton) {
            val sw=androidx.appcompat.widget.SwitchCompat(this).apply {
                text=label; textSize=16f; isChecked=source.isChecked
                setOnClickListener { if(source.isChecked != isChecked) source.performClick() }
            }
            box.addView(sw)
        }
        addMirror("Sesli komut",binding.switchVoice)
        addMirror("Görüntü stabilizasyonu",binding.switchStabilization)
        addMirror("Ekranı açık tut",binding.switchKeepScreenOn)
        val dialog=androidx.appcompat.app.AlertDialog.Builder(this).setTitle("Özellikler").setView(box)
            .setPositiveButton("TAMAM",null).setNegativeButton("İPTAL",null).create()
        group.setOnCheckedChangeListener { _,id ->
            val which=id-10040
            if(which !in values.indices)return@setOnCheckedChangeListener
            val selected=values[which]
            featurePrefs.edit().putString("camera_mode",selected).apply()
            if(selected=="single") toast("Tek Kamera seçildi.") else probeConcurrentCameraSupport(selected)
        }
        dialog.show()
    }

'''
s=s[:start]+newfun+s[end:]

# Move the status panel next to Start button where possible, using runtime re-parenting only.
# This is visual only and preserves all binding references.
needle='''        binding.btnGallery.visibility = android.view.View.GONE'''
extra=r'''        binding.btnGallery.visibility = android.view.View.GONE
        try {
            val startButton=binding.btnStartStop
            val startParent=startButton.parent as? android.widget.LinearLayout
            val statusView=binding.tvStatus.parent as? android.view.View
            if(startParent!=null && statusView!=null && statusView.parent!==startParent) {
                (statusView.parent as? android.view.ViewGroup)?.removeView(statusView)
                val oldIndex=startParent.indexOfChild(startButton)
                if(oldIndex>=0) {
                    startParent.removeView(startButton)
                    startParent.orientation=android.widget.LinearLayout.HORIZONTAL
                    startParent.gravity=android.view.Gravity.CENTER_VERTICAL
                    startParent.addView(statusView,android.widget.LinearLayout.LayoutParams(0,android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,1f))
                    startParent.addView(startButton,android.widget.LinearLayout.LayoutParams(0,android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,1f))
                }
            }
        } catch(t:Throwable) { reportMotoCamLogicIssue("v4.11 arayüz yerleşimi uygulanamadı: ${android.util.Log.getStackTraceString(t)}") }'''
s=s.replace(needle,extra,1)

kt.write_text(s,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts'); t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 41',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.11.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v4.11: UI-only layout; Gallery hidden; toggles in Features; Settings+Features bottom row; status beside Start; diagnostics preserved')
