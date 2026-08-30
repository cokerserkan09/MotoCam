from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')
start=s.find('    private fun showCommandSettings() {')
end=s.find('    private fun playRecordingStartedSound()', start)
if start<0 or end<0: raise SystemExit('settings block bulunamadi')
b=s[start:end]

# Ustteki uzun aciklama metnini tamamen kaldir.
b=re.sub(r'\n\s*\.setMessage\("Kaydı nasıl başlatıp durduracağınızı seçin\. Kablolu tuş modlarında aynı tuşa bir kez basmak kaydı başlatır, tekrar basmak durdurur\."\)', '', b, count=1)

# Ayarlar icerigini daha kompakt yap.
b=b.replace('val p = (20 * resources.displayMetrics.density).toInt(); setPadding(p, p / 2, p, 0)',
            'val p = (14 * resources.displayMetrics.density).toInt(); setPadding(p, 0, p, 0)',1)
b=b.replace('textSize = 17f','textSize = 15f')
b=b.replace('(14 * resources.displayMetrics.density).toInt()', '(8 * resources.displayMetrics.density).toInt()')
b=b.replace('(6 * resources.displayMetrics.density).toInt()', '(3 * resources.displayMetrics.density).toInt()')

# Secenek ve giris alanlarinin yazilarini kucult.
anchor='        val settingsScroll = android.widget.ScrollView(this).apply {'
if anchor not in b: raise SystemExit('settingsScroll bulunamadi')
compact='''        fun compactText(v: android.view.View) {
            if (v is android.widget.TextView) v.textSize = 15f
            if (v is android.view.ViewGroup) for (i in 0 until v.childCount) compactText(v.getChildAt(i))
        }
        compactText(box)
'''
b=b.replace(anchor, compact+anchor,1)

# Scroll alani daha kisa olsun; dialogun kendi KAYDET/IPTAL butonlari kesin gorunsun.
b=b.replace('(resources.displayMetrics.heightPixels * 0.55f).toInt()',
            '(resources.displayMetrics.heightPixels * 0.46f).toInt()',1)
# v3.7 sonradan pencereyi 0.88 ekrana zorluyorsa kaldir; Android dialog kendi uygun boyutunu secsin.
b=re.sub(r'\n\s*settingsDialog\.setOnShowListener \{.*?\n\s*\}\n\s*settingsDialog\.show\(\)', '\n        settingsDialog.show()', b, count=1, flags=re.S)

s=s[:start]+b+s[end:]
kt.write_text(s,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 29',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "3.8.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v3.8: aciklama kaldirildi, ayarlar kompakt, KAYDET/IPTAL icin alan ayrildi')
