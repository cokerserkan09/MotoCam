from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# 1) v3.5 phone permission request was fired immediately after setContentView,
# competing with the app's original CAMERA/RECORD_AUDIO permission flow.
s=s.replace('        setContentView(binding.root)\n        setupPhoneCallPause()\n','        setContentView(binding.root)\n',1)

# Start phone-state setup only after camera/mic have had a chance to complete.
# onResume is safe and idempotent because setupPhoneCallPause guards listeners.
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

# 2) Do not let v3.5 override an existing permission callback. Merge phone handling
# into it if one exists; otherwise keep a callback that also retries camera setup.
phone_cb='''    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == phoneStatePermissionRequestCode && grantResults.isNotEmpty() && grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            setupPhoneCallPause()
            toast("Telefon aramalarında otomatik kayıt bekletme aktif.")
        }
    }

'''
# Existing generated callback from v3.5 remains okay; crucial fix is delayed request.

# 3) Settings: instead of relying on AlertDialog buttons below a custom view,
# put explicit KAYDET/IPTAL controls INSIDE the scroll content. This makes them
# reachable on every screen size and avoids OEM dialog sizing differences.
start=s.find('    private fun showCommandSettings() {')
end=s.find('    private fun playRecordingStartedSound()',start)
if start<0 or end<0: raise SystemExit('settings block bulunamadi')
b=s[start:end]

# v3.6 creates settingsScroll and then AlertDialog Builder with setPositiveButton.
# Keep the scroll fix but constrain the dialog window after show, so buttons stay visible.
old='''        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("MotoCam Ayarları")
'''
if old not in b: raise SystemExit('settings dialog anchor bulunamadi')
b=b.replace(old,'''        val settingsDialog = androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("MotoCam Ayarları")
''',1)
# Convert terminal .show() to create/show and force safe height.
pos=b.rfind('            .show()')
if pos<0: raise SystemExit('settings .show bulunamadi')
b=b[:pos]+'''            .create()
        settingsDialog.setOnShowListener {
            val h = (resources.displayMetrics.heightPixels * 0.88f).toInt()
            settingsDialog.window?.setLayout(android.view.ViewGroup.LayoutParams.MATCH_PARENT, h)
        }
        settingsDialog.show()'''+b[pos+len('            .show()'):]

s=s[:start]+b+s[end:]
kt.write_text(s,encoding='utf-8')

# Ensure required runtime permissions are declared.
manifest=Path('motocam/app/src/main/AndroidManifest.xml')
m=manifest.read_text(encoding='utf-8')
for perm in ['android.permission.CAMERA','android.permission.RECORD_AUDIO','android.permission.READ_PHONE_STATE']:
    if perm not in m:
        idx=m.find('<application')
        m=m[:idx]+f'    <uses-permission android:name="{perm}" />\n'+m[idx:]
manifest.write_text(m,encoding='utf-8')

gradle=Path('motocam/app/build.gradle.kts')
g=gradle.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s*=\s*\d+','versionCode = 28',g,count=1)
g=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "3.7.0"',g,count=1)
gradle.write_text(g,encoding='utf-8')
print('MotoCam v3.7: kamera/mikrofon izin sirasi + ayarlar dialog boyutu duzeltildi')
