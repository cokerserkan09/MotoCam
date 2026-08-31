from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# v4.12: UI-only professional control panel. Preserve camera/recording/audio/voice/diagnostics logic.
needle='        applyCameraFeatureMode()'
ui=r'''        // v4.12 professional collapsible control panel (UI only)
        try {
            fun allViews(root: android.view.View): List<android.view.View> {
                val out=java.util.ArrayList<android.view.View>()
                fun walk(v: android.view.View) { out.add(v); if (v is android.view.ViewGroup) for(i in 0 until v.childCount) walk(v.getChildAt(i)) }
                walk(root); return out
            }
            allViews(binding.root).filterIsInstance<android.widget.TextView>().firstOrNull {
                it.text?.toString()?.trim()?.startsWith("Not:") == true
            }?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }

            val start=binding.btnRecord
            val root=binding.root
            val oldParent=start.parent as? android.view.ViewGroup
            val status=binding.tvStatus.parent as? android.view.View
            val statusParent=status?.parent as? android.view.ViewGroup
            if(oldParent!=null && status!=null && statusParent!=null && statusParent!==root) {
                statusParent.removeView(status)
                oldParent.removeView(start)

                val oldButtons=allViews(root).filterIsInstance<android.widget.Button>().filter {
                    val t=it.text?.toString()?.trim(); t=="AYARLAR" || t=="ÖZELLİKLER"
                }
                oldButtons.forEach { (it.parent as? android.view.ViewGroup)?.removeView(it) }

                val density=resources.displayMetrics.density
                fun dp(v:Int)=(v*density).toInt()
                val panel=android.widget.LinearLayout(this).apply {
                    orientation=android.widget.LinearLayout.VERTICAL
                    setPadding(dp(12),dp(10),dp(12),dp(10))
                    background=android.graphics.drawable.GradientDrawable().apply {
                        cornerRadius=dp(18).toFloat(); setColor(0xCC17171CL.toInt()); setStroke(dp(1),0x664C4C55)
                    }
                }
                val statusCard=android.widget.FrameLayout(this).apply {
                    setPadding(dp(12),dp(8),dp(12),dp(8))
                    background=android.graphics.drawable.GradientDrawable().apply {
                        cornerRadius=dp(14).toFloat(); setColor(0xB823232CL.toInt()); setStroke(dp(1),0x554F4F5C)
                    }
                }
                statusCard.addView(status,android.widget.FrameLayout.LayoutParams(-1,-2))
                panel.addView(statusCard,android.widget.LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(10)})

                val actionRow=android.widget.LinearLayout(this).apply { orientation=android.widget.LinearLayout.HORIZONTAL; gravity=android.view.Gravity.CENTER_VERTICAL }
                start.backgroundTintList=android.content.res.ColorStateList.valueOf(0xFF9B63EEL.toInt())
                start.setTextColor(android.graphics.Color.WHITE)
                start.textSize=18f
                actionRow.addView(start,android.widget.LinearLayout.LayoutParams(0,dp(64),1f).apply{rightMargin=dp(10)})
                val more=android.widget.Button(this).apply {
                    text="•••"; textSize=22f; setTextColor(android.graphics.Color.WHITE); isAllCaps=false
                    background=android.graphics.drawable.GradientDrawable().apply { cornerRadius=dp(16).toFloat(); setColor(0xFF26262DL.toInt()); setStroke(dp(1),0xFF55555FL.toInt()) }
                }
                actionRow.addView(more,android.widget.LinearLayout.LayoutParams(dp(76),dp(64)))
                panel.addView(actionRow)

                val menu=android.widget.LinearLayout(this).apply { orientation=android.widget.LinearLayout.VERTICAL; visibility=android.view.View.GONE; setPadding(0,dp(10),0,0) }
                fun menuButton(label:String, click:()->Unit)=android.widget.Button(this).apply {
                    text=label; textSize=17f; gravity=android.view.Gravity.START or android.view.Gravity.CENTER_VERTICAL; setPadding(dp(18),0,dp(12),0); setTextColor(android.graphics.Color.WHITE); isAllCaps=false
                    background=android.graphics.drawable.GradientDrawable().apply { cornerRadius=dp(12).toFloat(); setColor(0xFF292930L.toInt()); setStroke(dp(1),0xFF45454EL.toInt()) }
                    setOnClickListener { click() }
                }
                val settings=menuButton("⚙  AYARLAR") { showCommandSettings() }
                val features=menuButton("☷  ÖZELLİKLER") { showFeatureSettings() }
                menu.addView(settings,android.widget.LinearLayout.LayoutParams(-1,dp(58)).apply{bottomMargin=dp(6)})
                menu.addView(features,android.widget.LinearLayout.LayoutParams(-1,dp(58)))
                panel.addView(menu)
                more.setOnClickListener { menu.visibility=if(menu.visibility==android.view.View.VISIBLE) android.view.View.GONE else android.view.View.VISIBLE }

                oldParent.addView(panel,android.widget.LinearLayout.LayoutParams(-1,-2).apply{setMargins(dp(10),dp(8),dp(10),dp(10))})
            }
        } catch(t:Throwable) {
            reportMotoCamLogicIssue("v4.12 kontrol paneli arayüzü uygulanamadı.\n${android.util.Log.getStackTraceString(t)}")
        }
'''
if 'v4.12 professional collapsible control panel' not in s:
    if needle not in s: raise SystemExit('v4.12 UI anchor bulunamadi')
    pos=s.find(needle)
    s=s[:pos+len(needle)]+'\n'+ui+s[pos+len(needle):]

kt.write_text(s,encoding='utf-8')
g=Path('motocam/app/build.gradle.kts'); t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 42',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.12.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v4.12: professional bottom control panel, note removed, collapsible Settings/Features menu')
