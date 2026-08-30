from pathlib import Path

p=Path('.github/scripts/v39_real_playback_capture_patch.py')
s=p.read_text(encoding='utf-8')
start=s.find('# Kayit baslamadan once gercek playback capture servisini baslat.')
end=s.find('# Finalize aninda AAC sesini video ile mux et.', start)
if start < 0 or end < 0:
    raise SystemExit('v39 bolumu bulunamadi')
new='''# Kayit baslamadan once gercek playback capture servisini baslat.
startpos=s.find('    private fun startRecording() {')
endpos=s.find('    private fun ', startpos+20)
if startpos < 0 or endpos < 0: raise SystemExit('startRecording block bulunamadi')
rb=s[startpos:endpos]
anchor='        val recording = pendingRecording\\n'
if anchor not in rb: raise SystemExit('pendingRecording anchor bulunamadi')
insert=''' + "'''" + '''        if ((selectedVideoAudio == "playback" || selectedVideoAudio == "mixed") && !startPlaybackCaptureIfNeeded()) {
            toast("Medya sesi yakalama izni gerekli.")
            requestPlaybackCapturePermission()
            return
        }
        val recording = pendingRecording
''' + "'''" + '''
rb=rb.replace(anchor, insert, 1)
s=s[:startpos]+rb+s[endpos:]

'''
s=s[:start]+new+s[end:]
p.write_text(s,encoding='utf-8')
print('v3.9 anchor duzeltildi')
