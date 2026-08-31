from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

# v4.7'nin OEM FEATURE_CAMERA_CONCURRENT kapisini kaldir. Gercek CameraX kombinasyonlarini sorgula.
old='''                if (selected != "single" && !packageManager.hasSystemFeature(android.content.pm.PackageManager.FEATURE_CAMERA_CONCURRENT)) {
                    reportMotoCamLogicIssue("Çift kamera modu seçildi ancak cihaz FEATURE_CAMERA_CONCURRENT desteği bildirmiyor. Tek Kamera modu korunuyor.")
                    return@setSingleChoiceItems
                }
                featurePrefs.edit().putString("camera_mode", selected).apply()
                dialog.dismiss()
                if (selected == "single") toast("Tek Kamera seçildi.")
                else toast(if (selected == "dual_small") "Çift Kamera • Küçük seçildi." else "Çift Kamera • Yarım seçildi.")
                applyCameraFeatureMode()
'''
new='''                featurePrefs.edit().putString("camera_mode", selected).apply()
                dialog.dismiss()
                if (selected == "single") {
                    toast("Tek Kamera seçildi.")
                    applyCameraFeatureMode()
                } else {
                    toast(if (selected == "dual_small") "Çift Kamera • Küçük seçildi • kamera desteği kontrol ediliyor" else "Çift Kamera • Yarım seçildi • kamera desteği kontrol ediliyor")
                    probeConcurrentCameraSupport(selected)
                }
'''
if old not in s: raise SystemExit('v4.7 secim blogu bulunamadi')
s=s.replace(old,new,1)

start=s.find('    private fun applyCameraFeatureMode() {')
end=s.find('\n    private fun playRecordingStartedSound()', start)
if start<0 or end<0: raise SystemExit('v4.7 applyCameraFeatureMode bulunamadi')
block=r'''    private fun appVersionForDiagnostics(): String = try {
        packageManager.getPackageInfo(packageName, 0).versionName ?: "?"
    } catch (_: Throwable) { "?" }

    private fun concurrentCameraReport(provider: androidx.camera.lifecycle.ProcessCameraProvider): String {
        val combos = provider.availableConcurrentCameraInfos
        val details = combos.mapIndexed { i, list ->
            val lenses = list.joinToString("+") { info ->
                when (info.lensFacing) {
                    androidx.camera.core.CameraSelector.LENS_FACING_FRONT -> "ÖN"
                    androidx.camera.core.CameraSelector.LENS_FACING_BACK -> "ARKA"
                    else -> "DİĞER"
                }
            }
            "${i + 1}:$lenses"
        }.joinToString(", ")
        return "MotoCam çalışma raporu\nSürüm: ${appVersionForDiagnostics()}\nAndroid: ${android.os.Build.VERSION.SDK_INT}\nCihaz: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}\nFEATURE_CAMERA_CONCURRENT: ${packageManager.hasSystemFeature(android.content.pm.PackageManager.FEATURE_CAMERA_CONCURRENT)}\nCameraX concurrent kombinasyon sayısı: ${combos.size}\nKombinasyonlar: ${if (details.isBlank()) "yok" else details}"
    }

    private fun probeConcurrentCameraSupport(mode: String) {
        try {
            val future = androidx.camera.lifecycle.ProcessCameraProvider.getInstance(this)
            future.addListener({
                try {
                    val provider = future.get()
                    val pair = provider.availableConcurrentCameraInfos.firstOrNull { list ->
                        list.any { it.lensFacing == androidx.camera.core.CameraSelector.LENS_FACING_FRONT } &&
                        list.any { it.lensFacing == androidx.camera.core.CameraSelector.LENS_FACING_BACK }
                    }
                    if (pair == null) {
                        featurePrefs.edit().putString("camera_mode", "single").apply()
                        val report = concurrentCameraReport(provider) + "\n\nÖn+arka kamera CameraX tarafından üçüncü taraf uygulamaya eşzamanlı açılmıyor. Telefonun üretici kamera uygulaması kendi özel kamera yolunu kullanabiliyor olabilir. Tek Kamera moduna dönüldü."
                        reportMotoCamLogicIssue(report)
                        binding.tvStatus.text = "Hazır • Tek Kamera"
                    } else {
                        binding.tvStatus.text = if (mode == "dual_small") "Hazır • Çift Kamera / Küçük" else "Hazır • Çift Kamera / Yarım"
                        // Bu aşamada gerçek destek doğrulandı. Bir sonraki bind denemesinde hata olursa kalıcı tanı sistemi raporlayacak.
                        toast("CameraX ön + arka eşzamanlı kamera desteğini doğruladı.")
                    }
                } catch (t: Throwable) {
                    featurePrefs.edit().putString("camera_mode", "single").apply()
                    reportMotoCamLogicIssue("Çift kamera CameraX sorgusu başarısız. Sürüm: ${appVersionForDiagnostics()}\n${android.util.Log.getStackTraceString(t)}")
                }
            }, androidx.core.content.ContextCompat.getMainExecutor(this))
        } catch (t: Throwable) {
            featurePrefs.edit().putString("camera_mode", "single").apply()
            reportMotoCamLogicIssue("Çift kamera sağlayıcısı başlatılamadı. Sürüm: ${appVersionForDiagnostics()}\n${android.util.Log.getStackTraceString(t)}")
        }
    }

    private fun applyCameraFeatureMode() {
        val mode = cameraFeatureMode()
        if (mode == "single") {
            binding.tvStatus.text = "Hazır • Tek Kamera"
            return
        }
        probeConcurrentCameraSupport(mode)
    }
'''
s=s[:start]+block+s[end:]

# Hata raporlarinda sabit 4.5.0 yazisini gercek paket surumune cevir.
s=s.replace('Sürüm: 4.5.0', 'Sürüm: ${appVersionForDiagnostics()}')
s=s.replace('Surum: 4.5.0', 'Surum: ${appVersionForDiagnostics()}')

kt.write_text(s,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 38',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.8.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v4.8: FEATURE kapisi kaldirildi; CameraX availableConcurrentCameraInfos probe + dinamik surum tani; diagnostics preserved')
