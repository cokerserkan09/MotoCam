from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')

start = s.find('    private fun showCommandSettings() {')
end = s.find('    private fun playRecordingStartedSound()', start)
if start < 0 or end < 0:
    raise SystemExit('settings block bulunamadi')
b = s[start:end]

# v3.3 ScrollView'i dogrudan setView(...) icinde olusturuyor. Onu isimli bir
# ScrollView'e cevirip yuksekligini ekranin bir kismina sinirliyoruz. Boylece
# icerik kayar, AlertDialog'un KAYDET / IPTAL dugmeleri ekran disina cikmaz.
inline_scroll = '.setView(android.widget.ScrollView(this).apply { addView(box) })'
if inline_scroll not in b:
    raise SystemExit('v3.3 inline ScrollView bulunamadi')

builder_anchor = '        androidx.appcompat.app.AlertDialog.Builder(this)\n'
if builder_anchor not in b:
    raise SystemExit('AlertDialog Builder bulunamadi')

scroll_decl = '''        val settingsScroll = android.widget.ScrollView(this).apply {
            addView(box)
            isFillViewport = false
            overScrollMode = android.view.View.OVER_SCROLL_ALWAYS
            layoutParams = android.view.ViewGroup.LayoutParams(
                android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                (resources.displayMetrics.heightPixels * 0.55f).toInt()
            )
        }
        androidx.appcompat.app.AlertDialog.Builder(this)
'''

b = b.replace(builder_anchor, scroll_decl, 1)
b = b.replace(inline_scroll, '.setView(settingsScroll)', 1)
s = s[:start] + b + s[end:]

kt.write_text(s, encoding='utf-8')

gradle = Path('motocam/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 27', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "3.6.0"', g, count=1)
gradle.write_text(g, encoding='utf-8')

print('MotoCam v3.6: ayarlar kaydirilabilir, KAYDET ve IPTAL dugmeleri gorunur')
