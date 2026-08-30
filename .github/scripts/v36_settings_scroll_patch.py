from pathlib import Path
import re

kt = Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s = kt.read_text(encoding='utf-8')

start = s.find('    private fun showCommandSettings() {')
end = s.find('    private fun playRecordingStartedSound()', start)
if start < 0 or end < 0:
    raise SystemExit('settings block bulunamadi')
b = s[start:end]

# Dialog content is already a ScrollView in v3.3+. The problem is the positive
# button lives below the oversized dialog content on short screens. Constrain
# the scroll area to the visible screen and keep the dialog buttons reachable.
needle = '        val scroll = android.widget.ScrollView(this)\n'
if needle not in b:
    raise SystemExit('ScrollView anchor bulunamadi')

# Give the ScrollView a strict max-height by wrapping its child in a layout and
# applying a screen-relative height before showing the AlertDialog.
show_anchor = '            .setView(scroll)\n'
if show_anchor not in b:
    raise SystemExit('setView(scroll) anchor bulunamadi')

# Replace plain show() with a dialog variable so window/content can be resized.
old_show = '            .show()\n'
if old_show not in b:
    raise SystemExit('dialog show anchor bulunamadi')
new_show = '''            .create()
        dialog.setOnShowListener {
            val maxHeight = (resources.displayMetrics.heightPixels * 0.82f).toInt()
            scroll.layoutParams = android.widget.FrameLayout.LayoutParams(
                android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                maxHeight
            )
            scroll.isFillViewport = false
            scroll.overScrollMode = android.view.View.OVER_SCROLL_ALWAYS
            dialog.window?.setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        }
        dialog.show()
'''
b = b.replace(old_show, new_show, 1)
s = s[:start] + b + s[end:]

kt.write_text(s, encoding='utf-8')

gradle = Path('motocam/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 27', g, count=1)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "3.6.0"', g, count=1)
gradle.write_text(g, encoding='utf-8')
print('MotoCam v3.6: ayarlar kaydirma alani sinirlandi, Kaydet/Iptal butonlari ekranda')
