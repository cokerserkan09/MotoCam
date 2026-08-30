from pathlib import Path

p=Path('.github/scripts/v39_real_playback_capture_patch.py')
s=p.read_text(encoding='utf-8')
start=s.find('# Kayit baslamadan once gercek playback capture servisini baslat.')
end=s.find('# Finalize aninda AAC sesini video ile mux et.', start)
if start < 0 or end < 0:
    raise SystemExit('v39 bolumu bulunamadi')
new='''# Kayit baslamadan once gercek playback capture servisini baslat.
marker='    private fun startRecording() {\\n'
if marker not in s: raise SystemExit('startRecording bulunamadi')
insert=''' + "'''" + '''    private fun startRecording() {
        val realPlaybackMode = videoAudioSource()
        if ((realPlaybackMode == "playback" || realPlaybackMode == "mixed") && !startPlaybackCaptureIfNeeded()) {
            toast("Medya sesi yakalama izni gerekli.")
            requestPlaybackCapturePermission()
            return
        }
''' + "'''" + '''
s=s.replace(marker, insert, 1)

'''
s=s[:start]+new+s[end:]
p.write_text(s,encoding='utf-8')
print('v3.9 kayit baslangic eklemesi duzeltildi')
