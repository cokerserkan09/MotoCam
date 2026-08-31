from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')
needle='        applyCameraFeatureMode()'
ui=r'''        // v4.12 professional collapsible control panel - forced UI placement
        binding.root.post {
          try {
            fun views(root: android.view.View): List<android.view.View> {
              val out=java.util.ArrayList<android.view.View>()
              fun walk(v: android.view.View){ out.add(v); if(v is android.view.ViewGroup) for(i in 0 until v.childCount) walk(v.getChildAt(i)) }
              walk(root); return out
            }
            val root=binding.root
            val density=resources.displayMetrics.density
            fun dp(v:Int)=(v*density).toInt()

            // Remove note and old permanent Settings/Features row.
            views(root).filterIsInstance<android.widget.TextView>().filter { it.text?.toString()?.trim()?.startsWith("Not:")==true }.forEach { (it.parent as? android.view.ViewGroup)?.removeView(it) }
            views(root).filterIsInstance<android.widget.Button>().filter { val t=it.text?.toString()?.trim(); t=="AYARLAR" || t=="ÖZELLİKLER" }.forEach { (it.parent as? android.view.ViewGroup)?.removeView(it) }

            val start=binding.btnRecord
            val statusViews=listOf<android.view.View>(binding.tvStatus,binding.tvTimer,binding.tvVoice,binding.tvStabilization)
            statusViews.forEach { (it.parent as? android.view.ViewGroup)?.removeView(it) }
            (start.parent as? android.view.ViewGroup)?.removeView(start)

            val panel=android.widget.LinearLayout(this).apply {
              orientation=android.widget.LinearLayout.VERTICAL
              setPadding(dp(12),dp(10),dp(12),dp(10))
              background=android.graphics.drawable.GradientDrawable().apply { cornerRadius=dp(18).toFloat(); setColor(0xE817171CL.toInt()); setStroke(dp(1),0x665A5A66) }
              elevation=dp(12).toFloat()
            }
            val statusRow=android.widget.LinearLayout(this).apply { orientation=android.widget.LinearLayout.HORIZONTAL; gravity=android.view.Gravity.CENTER_VERTICAL }
            val left=android.widget.LinearLayout(this).apply { orientation=android.widget.LinearLayout.VERTICAL }
            val right=android.widget.LinearLayout(this).apply { orientation=android.widget.LinearLayout.VERTICAL; setPadding(dp(14),0,0,0) }
            binding.tvStatus.setTextColor(0xFFB47CFF.toInt()); binding.tvStatus.textSize=16f
            binding.tvTimer.setTextColor(android.graphics.Color.WHITE); binding.tvTimer.textSize=32f
            binding.tvVoice.setTextColor(0xFFE4E1E8.toInt()); binding.tvVoice.textSize=14f
            binding.tvStabilization.setTextColor(0xFFE4E1E8.toInt()); binding.tvStabilization.textSize=14f
            left.addView(binding.tvStatus); left.addView(binding.tvTimer)
            right.addView(binding.tvVoice); right.addView(binding.tvStabilization)
            statusRow.addView(left,android.widget.LinearLayout.LayoutParams(0,-2,1f))
            statusRow.addView(right,android.widget.LinearLayout.LayoutParams(0,-2,1.15f))
            panel.addView(statusRow,android.widget.LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(10)})

            val action=android.widget.LinearLayout(this).apply { orientation=android.widget.LinearLayout.HORIZONTAL; gravity=android.view.Gravity.CENTER_VERTICAL }
            start.backgroundTintList=android.content.res.ColorStateList.valueOf(0xFFAA72F5.toInt()); start.setTextColor(android.graphics.Color.BLACK); start.textSize=18f
            action.addView(start,android.widget.LinearLayout.LayoutParams(0,dp(64),1f).apply{rightMargin=dp(10)})
            val more=android.widget.Button(this).apply {
              text="•••"; textSize=24f; isAllCaps=false; setTextColor(android.graphics.Color.WHITE)
              background=android.graphics.drawable.GradientDrawable().apply { cornerRadius=dp(15).toFloat(); setColor(0xFF25252C.toInt()); setStroke(dp(1),0xFF555560.toInt()) }
            }
            action.addView(more,android.widget.LinearLayout.LayoutParams(dp(78),dp(64)))
            panel.addView(action)

            val menu=android.widget.LinearLayout(this).apply { orientation=android.widget.LinearLayout.VERTICAL; visibility=android.view.View.GONE; setPadding(0,dp(10),0,0) }
            fun menuButton(label:String, click:()->Unit)=android.widget.Button(this).apply {
              text=label; textSize=17f; isAllCaps=false; gravity=android.view.Gravity.START or android.view.Gravity.CENTER_VERTICAL; setPadding(dp(18),0,dp(12),0); setTextColor(android.graphics.Color.WHITE)
              background=android.graphics.drawable.GradientDrawable().apply { cornerRadius=dp(12).toFloat(); setColor(0xFF292930.toInt()); setStroke(dp(1),0xFF484852.toInt()) }
              setOnClickListener { click() }
            }
            menu.addView(menuButton("⚙  AYARLAR"){showCommandSettings()},android.widget.LinearLayout.LayoutParams(-1,dp(58)).apply{bottomMargin=dp(6)})
            menu.addView(menuButton("☷  ÖZELLİKLER"){showFeatureSettings()},android.widget.LinearLayout.LayoutParams(-1,dp(58)))
            panel.addView(menu)
            more.setOnClickListener { menu.visibility=if(menu.visibility==android.view.View.VISIBLE) android.view.View.GONE else android.view.View.VISIBLE }

            // Overlay directly on the root so old layout hierarchy cannot block the redesign.
            val host=root as android.view.ViewGroup
            val lp=android.widget.FrameLayout.LayoutParams(android.view.ViewGroup.LayoutParams.MATCH_PARENT,android.view.ViewGroup.LayoutParams.WRAP_CONTENT,android.view.Gravity.BOTTOM).apply { setMargins(dp(10),dp(10),dp(10),dp(12)) }
            host.addView(panel,lp)
          } catch(t:Throwable) {
            reportMotoCamLogicIssue("v4.12 kontrol paneli uygulanamadı.\n${android.util.Log.getStackTraceString(t)}")
          }
        }
'''
if 'v4.12 professional collapsible control panel - forced UI placement' not in s:
    if needle not in s: raise SystemExit('v4.12 UI anchor bulunamadi')
    pos=s.find(needle); s=s[:pos+len(needle)]+'\n'+ui+s[pos+len(needle):]
kt.write_text(s,encoding='utf-8')
g=Path('motocam/app/build.gradle.kts'); t=g.read_text(encoding='utf-8'); t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 43',t,count=1); t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.12.1"',t,count=1); g.write_text(t,encoding='utf-8')
print('MotoCam v4.12.1 forced professional bottom overlay control panel')
