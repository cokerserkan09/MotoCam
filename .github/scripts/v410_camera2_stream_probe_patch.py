from pathlib import Path
import re

kt=Path('motocam/app/src/main/java/com/motocam/app/MainActivity.kt')
s=kt.read_text(encoding='utf-8')
start=s.find('    private fun camera2DirectProbe(mode: String) {')
end=s.find('    private fun probeConcurrentCameraSupport(mode: String) {', start)
if start < 0 or end < 0: raise SystemExit('v4.9 Camera2 probe blogu bulunamadi')

helper=r'''    private fun camera2DirectProbe(mode: String) {
        if (androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            featurePrefs.edit().putString("camera_mode", "single").apply()
            reportMotoCamLogicIssue("Camera2 stream testi yapılamadı: CAMERA izni yok. Sürüm: ${appVersionForDiagnostics()}")
            return
        }
        val manager = getSystemService(android.content.Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
        val handler = android.os.Handler(android.os.Looper.getMainLooper())
        try {
            val ids = manager.cameraIdList.toList()
            val front = ids.firstOrNull { manager.getCameraCharacteristics(it).get(android.hardware.camera2.CameraCharacteristics.LENS_FACING) == android.hardware.camera2.CameraCharacteristics.LENS_FACING_FRONT }
            val back = ids.firstOrNull { manager.getCameraCharacteristics(it).get(android.hardware.camera2.CameraCharacteristics.LENS_FACING) == android.hardware.camera2.CameraCharacteristics.LENS_FACING_BACK }
            if (front == null || back == null) {
                featurePrefs.edit().putString("camera_mode", "single").apply()
                reportMotoCamLogicIssue("Camera2 stream testi: ön/arka ID bulunamadı. IDs=$ids front=$front back=$back")
                return
            }
            try { androidx.camera.lifecycle.ProcessCameraProvider.getInstance(this).get().unbindAll() } catch (_: Throwable) {}

            val opened=linkedMapOf<String,android.hardware.camera2.CameraDevice>()
            val sessions=linkedMapOf<String,android.hardware.camera2.CameraCaptureSession>()
            val readers=linkedMapOf<String,android.media.ImageReader>()
            val frameCounts=linkedMapOf(front to 0, back to 0)
            var finished=false

            fun closeAll() {
                sessions.values.forEach { try { it.close() } catch (_:Throwable){} }
                opened.values.forEach { try { it.close() } catch (_:Throwable){} }
                readers.values.forEach { try { it.close() } catch (_:Throwable){} }
            }
            fun restore() { handler.postDelayed({ try { recreate() } catch (_:Throwable){} },700L) }
            fun fail(msg:String) {
                if(finished)return
                finished=true; closeAll()
                featurePrefs.edit().putString("camera_mode","single").apply()
                binding.tvStatus.text="Hazır • Tek Kamera"
                reportMotoCamLogicIssue("Camera2 gerçek stream/session testi başarısız.\nSürüm: ${appVersionForDiagnostics()}\nCihaz: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}\nIDs=$ids Ön=$front Arka=$back\nSessionlar=${sessions.keys}\nFrame sayıları=$frameCounts\n\n$msg")
                restore()
            }
            fun successIfStreaming() {
                if(finished)return
                if(sessions.size==2 && (frameCounts[front]?:0)>=3 && (frameCounts[back]?:0)>=3) {
                    finished=true
                    binding.tvStatus.text=if(mode=="dual_small") "Camera2 çift stream başarılı • Küçük" else "Camera2 çift stream başarılı • Yarım"
                    android.app.AlertDialog.Builder(this)
                        .setTitle("MotoCam çift kamera stream testi başarılı")
                        .setMessage("Ön ve arka kamera aynı anda capture session kurdu ve ikisinden de gerçek görüntü kareleri alındı.\n\nÖn: $front (${frameCounts[front]}+ kare)\nArka: $back (${frameCounts[back]}+ kare)\n\nBu sonuç çift görüntü altyapısının cihazda gerçekten çalıştığını doğrular.")
                        .setPositiveButton("Tamam") { _,_-> closeAll(); restore() }
                        .setOnCancelListener { closeAll(); restore() }
                        .show()
                }
            }
            fun createSession(id:String, camera:android.hardware.camera2.CameraDevice) {
                val chars=manager.getCameraCharacteristics(id)
                val map=chars.get(android.hardware.camera2.CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                val sizes=map?.getOutputSizes(android.graphics.ImageFormat.YUV_420_888)?.toList().orEmpty()
                val size=sizes.filter { it.width<=640 && it.height<=480 }.maxByOrNull { it.width*it.height }
                    ?: sizes.minByOrNull { it.width*it.height }
                    ?: run { fail("YUV boyutu yok id=$id"); return }
                val reader=android.media.ImageReader.newInstance(size.width,size.height,android.graphics.ImageFormat.YUV_420_888,2)
                readers[id]=reader
                reader.setOnImageAvailableListener({ r ->
                    try { r.acquireLatestImage()?.close(); frameCounts[id]=(frameCounts[id]?:0)+1; successIfStreaming() } catch(t:Throwable){ fail("Frame okuma hatası id=$id: ${t.message}") }
                },handler)
                camera.createCaptureSession(listOf(reader.surface),object:android.hardware.camera2.CameraCaptureSession.StateCallback(){
                    override fun onConfigured(session:android.hardware.camera2.CameraCaptureSession){
                        if(finished){session.close();return}
                        sessions[id]=session
                        try {
                            val req=camera.createCaptureRequest(android.hardware.camera2.CameraDevice.TEMPLATE_PREVIEW).apply { addTarget(reader.surface) }.build()
                            session.setRepeatingRequest(req,null,handler)
                        } catch(t:Throwable){ fail("Repeating request başarısız id=$id: ${android.util.Log.getStackTraceString(t)}") }
                    }
                    override fun onConfigureFailed(session:android.hardware.camera2.CameraCaptureSession){ fail("CaptureSession onConfigureFailed id=$id") }
                },handler)
            }
            fun maybeSessions(){ if(opened.size==2){ createSession(back,opened[back]!!); createSession(front,opened[front]!!) } }
            fun open(id:String){
                manager.openCamera(id,object:android.hardware.camera2.CameraDevice.StateCallback(){
                    override fun onOpened(camera:android.hardware.camera2.CameraDevice){ if(finished){camera.close();return}; opened[id]=camera; maybeSessions() }
                    override fun onDisconnected(camera:android.hardware.camera2.CameraDevice){ camera.close(); if(!finished) fail("Kamera bağlantısı kesildi id=$id") }
                    override fun onError(camera:android.hardware.camera2.CameraDevice,error:Int){ camera.close(); if(!finished) fail("CameraDevice.onError id=$id error=$error (1=IN_USE,2=MAX_CAMERAS_IN_USE,3=DISABLED,4=DEVICE,5=SERVICE)") }
                },handler)
            }
            open(back); open(front)
            handler.postDelayed({ if(!finished) fail("10 saniyede iki aktif stream doğrulanamadı") },10000L)
        } catch(t:Throwable){
            featurePrefs.edit().putString("camera_mode","single").apply()
            reportMotoCamLogicIssue("Camera2 stream test exception. Sürüm: ${appVersionForDiagnostics()}\n${android.util.Log.getStackTraceString(t)}")
            handler.postDelayed({try{recreate()}catch(_:Throwable){}},700L)
        }
    }

'''
s=s[:start]+helper+s[end:]
kt.write_text(s,encoding='utf-8')

g=Path('motocam/app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t=re.sub(r'versionCode\s*=\s*\d+','versionCode = 40',t,count=1)
t=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "4.10.0"',t,count=1)
g.write_text(t,encoding='utf-8')
print('MotoCam v4.10: Camera2 two real YUV capture sessions + frame proof; diagnostics preserved')
