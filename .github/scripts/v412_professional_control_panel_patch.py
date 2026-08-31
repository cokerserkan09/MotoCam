from pathlib import Path
import re
kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt'); s=kt.read_text(encoding='utf-8'); needle='        applyCameraFeatureMode()'
ui=r'''        // v4.13 final compact bottom control panel
        binding.root.post {
          try {
            fun views(root: android.view.View): List<android.view.View> { val out=java.util.ArrayList<android.view.View>(); fun walk(v:android.view.View){out.add(v);if(v is android.view.ViewGroup)for(i in 0 until v.childCount)walk(v.getChildAt(i))};walk(root);return out }
            val root=binding.root; val d=resources.displayMetrics.density; fun dp(v:Int)=(v*d).toInt()
            // Remove every legacy note/settings/features button before building the new panel.
            views(root).filterIsInstance<android.widget.TextView>().filter{it.text?.toString()?.trim()?.startsWith("Not:")==true}.forEach{(it.parent as? android.view.ViewGroup)?.removeView(it)}
            views(root).filterIsInstance<android.widget.Button>().filter{val t=it.text?.toString()?.trim();t=="AYARLAR"||t=="ÖZELLİKLER"}.forEach{(it.parent as? android.view.ViewGroup)?.removeView(it)}
            val start=binding.btnRecord; (start.parent as? android.view.ViewGroup)?.removeView(start)
            listOf<android.view.View>(binding.tvStatus,binding.tvTimer,binding.tvVoice,binding.tvStabilization).forEach{(it.parent as? android.view.ViewGroup)?.removeView(it)}
            val panel=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.VERTICAL;setPadding(dp(10),dp(9),dp(10),dp(9));background=android.graphics.drawable.GradientDrawable().apply{cornerRadius=dp(18).toFloat();setColor(0xE817171C.toInt());setStroke(dp(1),0x665A5A66)};elevation=dp(12).toFloat()}
            val row=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.HORIZONTAL;gravity=android.view.Gravity.CENTER_VERTICAL}
            val left=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.VERTICAL};val right=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.VERTICAL;setPadding(dp(12),0,0,0)}
            binding.tvStatus.setTextColor(0xFFB47CFF.toInt());binding.tvStatus.textSize=13f;binding.tvTimer.setTextColor(android.graphics.Color.WHITE);binding.tvTimer.textSize=26f;binding.tvVoice.setTextColor(0xFFE5E2E9.toInt());binding.tvVoice.textSize=12f;binding.tvStabilization.setTextColor(0xFFE5E2E9.toInt());binding.tvStabilization.textSize=12f
            left.addView(binding.tvStatus);left.addView(binding.tvTimer);right.addView(binding.tvVoice);right.addView(binding.tvStabilization);row.addView(left,android.widget.LinearLayout.LayoutParams(0,-2,1f));row.addView(right,android.widget.LinearLayout.LayoutParams(0,-2,1.1f));panel.addView(row,android.widget.LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(8)})
            val action=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.HORIZONTAL;gravity=android.view.Gravity.CENTER_VERTICAL};start.backgroundTintList=android.content.res.ColorStateList.valueOf(0xFFAA72F5.toInt());start.setTextColor(android.graphics.Color.BLACK);start.textSize=16f;action.addView(start,android.widget.LinearLayout.LayoutParams(0,dp(58),1f).apply{rightMargin=dp(9)})
            val more=android.widget.Button(this).apply{text="•••";textSize=21f;isAllCaps=false;setTextColor(android.graphics.Color.WHITE);background=android.graphics.drawable.GradientDrawable().apply{cornerRadius=dp(14).toFloat();setColor(0xFF25252C.toInt());setStroke(dp(1),0xFF555560.toInt())}};action.addView(more,android.widget.LinearLayout.LayoutParams(dp(72),dp(58)));panel.addView(action)
            val menu=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.VERTICAL;visibility=android.view.View.GONE;setPadding(0,dp(8),0,0)}
            fun mb(label:String,click:()->Unit)=android.widget.Button(this).apply{text=label;textSize=15f;isAllCaps=false;gravity=android.view.Gravity.START or android.view.Gravity.CENTER_VERTICAL;setPadding(dp(16),0,dp(10),0);setTextColor(android.graphics.Color.WHITE);background=android.graphics.drawable.GradientDrawable().apply{cornerRadius=dp(12).toFloat();setColor(0xFF292930.toInt());setStroke(dp(1),0xFF484852.toInt())};setOnClickListener{click()}}
            menu.addView(mb("⚙  AYARLAR"){showCommandSettings()},android.widget.LinearLayout.LayoutParams(-1,dp(52)).apply{bottomMargin=dp(5)});menu.addView(mb("☷  ÖZELLİKLER"){showFeatureSettings()},android.widget.LinearLayout.LayoutParams(-1,dp(52)));panel.addView(menu);more.setOnClickListener{menu.visibility=if(menu.visibility==android.view.View.VISIBLE)android.view.View.GONE else android.view.View.VISIBLE}
            val host=root as android.view.ViewGroup
            // Bottom overlay: safely above navigation area; status bar can never overlap it.
            val lp=android.widget.FrameLayout.LayoutParams(-1,-2,android.view.Gravity.BOTTOM).apply{setMargins(dp(18),dp(80),dp(18),dp(28))};host.addView(panel,lp)
            // Second pass removes any legacy bottom AYARLAR/ÖZELLİKLER views that were added later by old UI code, excluding our new menu descendants.
            root.postDelayed({ views(root).filterIsInstance<android.widget.Button>().filter{b-> val t=b.text?.toString()?.trim(); (t=="AYARLAR"||t=="ÖZELLİKLER") && b.parent!==menu}.forEach{(it.parent as? android.view.ViewGroup)?.removeView(it)} },250)
          }catch(t:Throwable){reportMotoCamLogicIssue("v4.13 kontrol paneli uygulanamadı.\n${android.util.Log.getStackTraceString(t)}")}
        }
'''
if 'v4.13 final compact bottom control panel' not in s:
    if needle not in s: raise SystemExit('UI anchor bulunamadi')
    pos=s.find(needle);s=s[:pos+len(needle)]+'\n'+ui+s[pos+len(needle):]
kt.write_text(s,encoding='utf-8')
g=Path('motocam/app/build.gradle.kts');t=g.read_text(encoding='utf-8');t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 44',t,count=1);t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.13.0"',t,count=1);g.write_text(t,encoding='utf-8');print('MotoCam v4.13 final compact bottom panel')
