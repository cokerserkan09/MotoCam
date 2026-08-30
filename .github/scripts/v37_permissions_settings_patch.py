from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# 1) Telefon izni kamera/mikrofon izin akisini kesmesin.
s=s.replace('        setContentView(binding.root)\n        setupPhoneCallPause()\n','        setContentView(binding.root)\n',1)

on_destroy=s.find('    override fun onDestroy()')
if on_destroy < 0: raise SystemExit('onDestroy bulunamadi')
if 'override fun onResume()' not in s:
    resume='''    override fun onResume() {
        super.onResume()
        binding.root.postDelayed({
            val cameraOk = androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA) == android.content.pm.PackageManager.PERMISSION_GRANTED
            val micOk = androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED
            if (cameraOk && micOk) setupPhoneCallPause()
        }, 1200)
    }

'''
    s=s[:on_destroy]+resume+s[on_destroy:]

# 2) Ayarlar penceresi: v3.6 son satiri .setNegativeButton(...).show() seklinde.
# Builder'i dialog degiskenine cevir ve show sonrasinda ekrana gore yukseklik ver.
start=s.find('    private fun showCommandSettings() {')
end=s.find('    private fun playRecordingStartedSound()',start)
if start<0 or end<0: raise SystemExit('settings block bulunamadi')
b=s[start:end]

old='''        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("MotoCam Ayarları")
'''
if old not in b: raise SystemExit('settings dialog anchor bulunamadi')
b=b.replace(old,'''        val settingsDialog = androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("MotoCam Ayarları")
''',1)

needle='.setNegativeButton("İPTAL", null).show()'
if needle in b:
    b=b.replace(needle,'.setNegativeButton("İPTAL", null).create()',1)
elif '.setNegativeButton("İPTAL", null)\n            .show()' in b:
    b=b.replace('.setNegativeButton("İPTAL", null)\n            .show()','.setNegativeButton("İPTAL", null)\n            .create()',1)
else:
    raise SystemExit('settings dialog show anchor bulunamadi')

# Add show + fixed safe height before function closes.
insert='''
        settingsDialog.setOnShowListener {
            val h = (resources.displayMetrics.heightPixels * 0.86f).toInt()
            settingsDialog.window?.setLayout(android.view.ViewGroup.LayoutParams.MATCH_PARENT, h)
        }
        settingsDialog.show()
'''
last_close=b.rfind('    }\n')
if last_close<0: raise SystemExit('settings function kapanisi bulunamadi')
b=b[:last_close]+insert+b[last_close:]
s=s[:start]+b+s[end:]

# 3) Gerekli izinler manifestte kesin bulunsun.
manifest=Path('motocam/app/src/main/AndroidManifest.xml')
m=manifest.read_text(encoding='utf-8')
for perm in ['android.permission.CAMERA','android.permission.RECORD_AUDIO','android.permission.READ_PHONE_STATE']:
    if perm not in m:
        idx=m.find('<application')
        m=m[:idx]+f'    <uses-permission android:name="{perm}" />\n'+m[idx:]
manifest.write_text(m,encoding='utf-8')

kt.write_text(s,encoding='utf-8')

gradle=Path('motocam/app/build.gradle.kts')
g=gradle.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s*=\s*\d+','versionCode = 28',g,count=1)
g=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "3.7.0"',g,count=1)
gradle.write_text(g,encoding='utf-8')
print('MotoCam v3.7: izin sirasi ve ayarlar dialogu duzeltildi')
