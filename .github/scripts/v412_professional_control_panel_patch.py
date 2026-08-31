from pathlib import Path
import re
kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt');s=kt.read_text(encoding='utf-8');needle='        applyCameraFeatureMode()'
ui=r'''        // v4.14 final UI: root-independent bottom positioning
        binding.root.post {
          try {
            fun views(r:android.view.View):List<android.view.View>{val o=java.util.ArrayList<android.view.View>();fun w(v:android.view.View){o.add(v);if(v is android.view.ViewGroup)for(i in 0 until v.childCount)w(v.getChildAt(i))};w(r);return o}
            val root=binding.root;val d=resources.displayMetrics.density;fun dp(v:Int)=(v*d).toInt()
            fun legacy(){
              try{(settingsButton.parent as? android.view.ViewGroup)?.removeView(settingsButton)}catch(_:Throwable){}
              views(root).filterIsInstance<android.widget.Button>().filter{val t=it.text?.toString()?.uppercase(java.util.Locale.ROOT)?:"";t.contains("AYARLAR")||t.contains("ÖZELLİKLER")}.forEach{(it.parent as? android.view.ViewGroup)?.removeView(it)}
              views(root).filterIsInstance<android.widget.TextView>().filter{it.text?.toString()?.trim()?.startsWith("Not:")==true}.forEach{(it.parent as? android.view.ViewGroup)?.removeView(it)}
            }
            legacy()
            val start=binding.btnRecord;(start.parent as? android.view.ViewGroup)?.removeView(start)
            listOf<android.view.View>(binding.tvStatus,binding.tvTimer,binding.tvVoice,binding.tvStabilization).forEach{(it.parent as? android.view.ViewGroup)?.removeView(it)}
            val panel=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.VERTICAL;setPadding(dp(10),dp(8),dp(10),dp(8));background=android.graphics.drawable.GradientDrawable().apply{cornerRadius=dp(16).toFloat();setColor(0xE817171C.toInt());setStroke(dp(1),0x665A5A66)};elevation=dp(16).toFloat()}
            val info=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.HORIZONTAL;gravity=android.view.Gravity.CENTER_VERTICAL}
            val l=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.VERTICAL};val r=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.VERTICAL;setPadding(dp(10),0,0,0)}
            binding.tvStatus.textSize=12f;binding.tvStatus.setTextColor(0xFFB47CFF.toInt());binding.tvTimer.textSize=24f;binding.tvTimer.setTextColor(android.graphics.Color.WHITE);binding.tvVoice.textSize=11f;binding.tvVoice.setTextColor(0xFFE5E2E9.toInt());binding.tvStabilization.textSize=11f;binding.tvStabilization.setTextColor(0xFFE5E2E9.toInt())
            l.addView(binding.tvStatus);l.addView(binding.tvTimer);r.addView(binding.tvVoice);r.addView(binding.tvStabilization);info.addView(l,android.widget.LinearLayout.LayoutParams(0,-2,1f));info.addView(r,android.widget.LinearLayout.LayoutParams(0,-2,1.15f));panel.addView(info,android.widget.LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(7)})
            val actions=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.HORIZONTAL};start.textSize=15f;start.setTextColor(android.graphics.Color.BLACK);start.backgroundTintList=android.content.res.ColorStateList.valueOf(0xFFAA72F5.toInt());actions.addView(start,android.widget.LinearLayout.LayoutParams(0,dp(54),1f).apply{rightMargin=dp(8)})
            val more=android.widget.Button(this).apply{text="•••";textSize=20f;isAllCaps=false;setTextColor(android.graphics.Color.WHITE);background=android.graphics.drawable.GradientDrawable().apply{cornerRadius=dp(13).toFloat();setColor(0xFF25252C.toInt());setStroke(dp(1),0xFF555560.toInt())}};actions.addView(more,android.widget.LinearLayout.LayoutParams(dp(68),dp(54)));panel.addView(actions)
            val menu=android.widget.LinearLayout(this).apply{orientation=android.widget.LinearLayout.VERTICAL;visibility=android.view.View.GONE;setPadding(0,dp(7),0,0)}
            fun b(txt:String,fn:()->Unit)=android.widget.Button(this).apply{text=txt;textSize=14f;isAllCaps=false;gravity=android.view.Gravity.START or android.view.Gravity.CENTER_VERTICAL;setPadding(dp(15),0,0,0);setTextColor(android.graphics.Color.WHITE);background=android.graphics.drawable.GradientDrawable().apply{cornerRadius=dp(11).toFloat();setColor(0xFF292930.toInt());setStroke(dp(1),0xFF484852.toInt())};setOnClickListener{fn()}}
            val nb1=b("⚙  AYARLAR"){showCommandSettings()};val nb2=b("☷  ÖZELLİKLER"){showFeatureSettings()};menu.addView(nb1,android.widget.LinearLayout.LayoutParams(-1,dp(48)).apply{bottomMargin=dp(4)});menu.addView(nb2,android.widget.LinearLayout.LayoutParams(-1,dp(48)));panel.addView(menu)
            val host=root as android.view.ViewGroup;host.addView(panel,android.view.ViewGroup.LayoutParams(root.width-dp(28),android.view.ViewGroup.LayoutParams.WRAP_CONTENT))
            fun place(){panel.x=dp(14).toFloat();panel.y=(root.height-panel.height-dp(24)).coerceAtLeast(dp(48)).toFloat();panel.bringToFront()}
            panel.post{place()}
            more.setOnClickListener{menu.visibility=if(menu.visibility==android.view.View.VISIBLE)android.view.View.GONE else android.view.View.VISIBLE;panel.post{place()}}
            root.postDelayed({
              try{(settingsButton.parent as? android.view.ViewGroup)?.removeView(settingsButton)}catch(_:Throwable){}
              views(root).filterIsInstance<android.widget.Button>().filter{it!==nb1&&it!==nb2}.filter{val t=it.text?.toString()?.uppercase(java.util.Locale.ROOT)?:"";t.contains("AYARLAR")||t.contains("ÖZELLİKLER")}.forEach{(it.parent as? android.view.ViewGroup)?.removeView(it)}
              place()
            },500)
          }catch(t:Throwable){reportMotoCamLogicIssue("v4.14 arayüz uygulanamadı.\n${android.util.Log.getStackTraceString(t)}")}
        }
'''
if 'v4.14 final UI: root-independent bottom positioning' not in s:
    if needle not in s:raise SystemExit('anchor yok')
    p=s.find(needle);s=s[:p+len(needle)]+'\n'+ui+s[p+len(needle):]
kt.write_text(s,encoding='utf-8')
g=Path('motocam/app/build.gradle.kts');t=g.read_text(encoding='utf-8');t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 45',t,count=1);t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.14.0"',t,count=1);g.write_text(t,encoding='utf-8');print('MotoCam v4.14 root-independent bottom UI')
