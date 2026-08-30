from pathlib import Path
import re

manifest = Path('motocam/app/src/main/AndroidManifest.xml')
s = manifest.read_text(encoding='utf-8')

# Android foreground service temel izni zorunludur. MediaProjection ve mixed/mikrofon
# modlari icin ilgili FGS izinlerini de acikca tanimla.
perms = [
    'android.permission.FOREGROUND_SERVICE',
    'android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION',
    'android.permission.FOREGROUND_SERVICE_MICROPHONE',
]
for perm in perms:
    if f'android:name="{perm}"' not in s:
        pos = s.find('<application')
        if pos < 0:
            raise SystemExit('application etiketi bulunamadi')
        s = s[:pos] + f'    <uses-permission android:name="{perm}" />\n' + s[pos:]

# PlaybackCaptureService kesin olarak mediaProjection; mixed modunda microphone tipini kullanir.
service_pat = re.compile(r'(<service\b[^>]*android:name="\.PlaybackCaptureService"[^>]*)(/?>)', re.S)
m = service_pat.search(s)
if m:
    tag = m.group(0)
    if 'android:foregroundServiceType=' not in tag:
        tag2 = tag[:-2] + ' android:foregroundServiceType="mediaProjection|microphone" />' if tag.endswith('/>') else tag[:-1] + ' android:foregroundServiceType="mediaProjection|microphone">'
        s = s[:m.start()] + tag2 + s[m.end():]
else:
    # v3.9 normalde servisi ekler; yoksa application icine ekle.
    close = s.rfind('</application>')
    if close < 0:
        raise SystemExit('application kapanisi bulunamadi')
    svc = '        <service android:name=".PlaybackCaptureService" android:exported="false" android:foregroundServiceType="mediaProjection|microphone" />\n'
    s = s[:close] + svc + s[close:]

manifest.write_text(s, encoding='utf-8')

g = Path('motocam/app/build.gradle.kts')
t = g.read_text(encoding='utf-8')
t = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 34', t, count=1)
t = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "4.4.0"', t, count=1)
g.write_text(t, encoding='utf-8')

print('MotoCam v4.4: FOREGROUND_SERVICE + mediaProjection + microphone FGS izinleri eklendi')
