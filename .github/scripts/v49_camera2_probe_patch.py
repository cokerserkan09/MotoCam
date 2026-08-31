from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')

marker='    private fun probeConcurrentCameraSupport(mode: String) {'
if marker not in s: raise SystemExit('v4.8 probe noktasi bulunamadi')

helper=r'''    private fun camera2DirectProbe(mode: String) {
        if (androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            featurePrefs.edit().putString("camera_mode", "single").apply()
            reportMotoCamLogicIssue("Camera2 doğrudan test yapılamadı: CAMERA izni yok. Sürüm: ${appVersionForDiagnostics()}")
            return
        }
        val manager = getSystemService(android.content.Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
        try {
            val ids = manager.cameraIdList.toList()
            val front = ids.firstOrNull { manager.getCameraCharacteristics(it).get(android.hardware.camera2.CameraCharacteristics.LENS_FACING) == android.hardware.camera2.CameraCharacteristics.LENS_FACING_FRONT }
            val back = ids.firstOrNull { manager.getCameraCharacteristics(it).get(android.hardware.camera2.CameraCharacteristics.LENS_FACING) == android.hardware.camera2.CameraCharacteristics.LENS_FACING_BACK }
            val advertised = if (android.os.Build.VERSION.SDK_INT >= 30) manager.concurrentCameraIds.joinToString("; ") { it.joinToString("+") } else "API<30"
            if (front == null || back == null) {
                featurePrefs.edit().putString("camera_mode", "single").apply()
                reportMotoCamLogicIssue("Camera2 test: ön veya arka kamera kimliği bulunamadı. IDs=$ids front=$front back=$back concurrent=$advertised")
                return
            }
            try { androidx.camera.lifecycle.ProcessCameraProvider.getInstance(this).get().unbindAll() } catch (_: Throwable) {}
            val opened = linkedMapOf<String, android.hardware.camera2.CameraDevice>()
            var finished = false
            fun finishFailure(message: String) {
                if (finished) return
                finished = true
                opened.values.forEach { try { it.close() } catch (_: Throwable) {} }
                featurePrefs.edit().putString("camera_mode", "single").apply()
                binding.tvStatus.text = "Hazır • Tek Kamera"
                reportMotoCamLogicIssue("Camera2 doğrudan ön+arka testi başarısız.\nSürüm: ${appVersionForDiagnostics()}\nCihaz: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}\nCamera IDs: $ids\nÖn: $front Arka: $back\nCamera2 advertised concurrent: $advertised\n\n$message")
                try { startCamera() } catch (_: Throwable) {}
            }
            fun successIfBoth() {
                if (finished || opened.size < 2) return
                finished = true
                opened.values.forEach { try { it.close() } catch (_: Throwable) {} }
                binding.tvStatus.text = if (mode == "dual_small") "Camera2 ön+arka açıldı • Küçük altyapısı uygun" else "Camera2 ön+arka açıldı • Yarım altyapısı uygun"
                android.app.AlertDialog.Builder(this)
                    .setTitle("MotoCam Camera2 testi başarılı")
                    .setMessage("Telefon CameraX listesinde göstermese de Camera2 ile ön ve arka kamera aynı anda açılabildi.\n\nÖn kamera: $front\nArka kamera: $back\n\nBir sonraki aşamada bu yol üzerinden çift görüntü ve kayıt bağlanabilir.")
                    .setPositiveButton("Tamam", null).show()
                try { startCamera() } catch (_: Throwable) {}
            }
            fun open(id: String) {
                manager.openCamera(id, object: android.hardware.camera2.CameraDevice.StateCallback() {
                    override fun onOpened(camera: android.hardware.camera2.CameraDevice) { opened[id]=camera; successIfBoth() }
                    override fun onDisconnected(camera: android.hardware.camera2.CameraDevice) { camera.close(); finishFailure("Kamera bağlantısı kesildi: id=$id") }
                    override fun onError(camera: android.hardware.camera2.CameraDevice, error: Int) { camera.close(); finishFailure("CameraDevice.onError id=$id error=$error (1=IN_USE, 2=MAX_CAMERAS_IN_USE, 3=DISABLED, 4=DEVICE, 5=SERVICE)") }
                }, null)
            }
            // Android concurrent camera contract: iki kamerayı da oturum kurmadan önce açmayı dene.
            open(back)
            open(front)
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                if (!finished && opened.size < 2) finishFailure("8 saniye içinde iki kamera birlikte açılamadı. Açılanlar=${opened.keys}")
            }, 8000L)
        } catch (t: Throwable) {
            featurePrefs.edit().putString("camera_mode", "single").apply()
            reportMotoCamLogicIssue("Camera2 doğrudan test exception. Sürüm: ${appVersionForDiagnostics()}\n${android.util.Log.getStackTraceString(t)}")
            try { startCamera() } catch (_: Throwable) {}
        }
    }

'''
s=s.replace(marker,helper+marker,1)

old='''                    if (pair == null) {
                        featurePrefs.edit().putString("camera_mode", "single").apply()
                        val report = concurrentCameraReport(provider) + "\\n\\nÖn+arka kamera CameraX tarafından üçüncü taraf uygulamaya eşzamanlı açılmıyor. Telefonun üretici kamera uygulaması kendi özel kamera yolunu kullanabiliyor olabilir. Tek Kamera moduna dönüldü."
                        reportMotoCamLogicIssue(report)
                        binding.tvStatus.text = "Hazır • Tek Kamera"
                    } else {'''
new='''                    if (pair == null) {
                        binding.tvStatus.text = "CameraX yok • Camera2 doğrudan test ediliyor"
                        camera2DirectProbe(mode)
                    } else {'''
if old not in s: raise SystemExit('v4.8 pair null blogu bulunamadi')
s=s.replace(old,new,1)

kt.write_text(s,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 39',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.9.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v4.9: CameraX yoksa Camera2 direct front+back open probe; permanent diagnostics preserved')
