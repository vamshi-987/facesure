import { useState, useRef, useCallback, useEffect } from "react";
import Webcam from "react-webcam";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function RegisterFace() {
  const webcamRef = useRef(null);
  const canvasRef = useRef(null);
  const navigate = useNavigate();

  const [imgSrc, setImgSrc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [permission, setPermission] = useState("prompt");
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const [validationMessage, setValidationMessage] = useState("");
  const [validationStatus, setValidationStatus] = useState(""); // "good", "warning", "error"

  const userId = localStorage.getItem("userId");
  const userType = localStorage.getItem("role") || "STUDENT";

  /* 🔒 BLOCK if already registered */
  useEffect(() => {
    const faceId = localStorage.getItem("face_id");
    if (faceId) {
      navigate("/student", { replace: true });
    }
  }, [navigate]);

  /* CAMERA PERMISSION */
  useEffect(() => {
    navigator.permissions?.query({ name: "camera" }).then((res) => {
      setPermission(res.state);
      res.onchange = () => setPermission(res.state);
    });
  }, []);

  /* CLEANUP CAMERA ON UNMOUNT */
  useEffect(() => {
    return () => {
      const stream = webcamRef.current?.video?.srcObject;
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  useEffect(() => {
  return () => {
    stopCamera();
  };
  }, []);
  
  useEffect(() => {
  const handlePageHide = () => {
    stopCamera();
  };

  window.addEventListener("pagehide", handlePageHide);

  return () => {
    window.removeEventListener("pagehide", handlePageHide);
  };
  }, []);
  
  useEffect(() => {
  const handleVisibilityChange = () => {
    if (document.visibilityState === "hidden") {
      stopCamera();
    }
  };

  document.addEventListener("visibilitychange", handleVisibilityChange);

  return () => {
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  };
  }, []);


  const requestCamera = async () => {
    setError("");
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setError("❌ Camera not supported. Use HTTPS and a modern browser (Chrome, Firefox, Safari, Edge).");
        setPermission("denied");
        return;
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: "user" }
      });
      stream.getTracks().forEach((t) => t.stop());
      setPermission("granted");
      setToast("✅ Camera permission granted!");
      setTimeout(() => setToast(null), 2000);
    } catch (err) {
      console.error("Camera permission error:", err);
      setPermission("denied");
      
      if (err.name === "NotAllowedError") {
        setError("❌ Camera permission denied. Click the camera icon in your address bar to allow.");
      } else if (err.name === "NotFoundError") {
        setError("❌ No camera found. Your device doesn't have a camera.");
      } else if (err.name === "NotReadableError") {
        setError("❌ Camera is locked or being used by another app. Close other apps and try again.");
      } else if (err.name === "SecurityError") {
        setError("❌ HTTPS required! Camera only works on secure connections. Use HTTPS URL.");
      } else {
        setError(`❌ Camera error: ${err.message}`);
      }
    }
  };

  const stopCamera = () => {
  const video = webcamRef.current?.video;
  if (video && video.srcObject) {
    const stream = video.srcObject;
    stream.getTracks().forEach(track => track.stop());
    video.srcObject = null; // 🔥 CRITICAL
  }
  };

  // Analyze video frame for face detection and lighting
  const analyzeFrame = useCallback(() => {
    const video = webcamRef.current?.video;
    const canvas = canvasRef.current;
    
    if (!video || !canvas || !cameraReady || video.readyState !== video.HAVE_ENOUGH_DATA) {
      return;
    }

    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    // Calculate average brightness (lighting check)
    let totalBrightness = 0;
    let pixelCount = 0;
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255;
      totalBrightness += brightness;
      pixelCount++;
    }
    const avgBrightness = totalBrightness / pixelCount;

    // Only do lighting-based guidance (face detection heuristics were too noisy)
    let message = "";
    let status = "good";

    if (avgBrightness < 0.25) {
      message = "⚠️ Lighting is too dark. Please move to a brighter area.";
      status = "warning";
    } else if (avgBrightness > 0.9) {
      message = "⚠️ Lighting is too bright. Please reduce glare or move to a shaded area.";
      status = "warning";
    } else if (avgBrightness < 0.4) {
      message = "💡 Lighting could be better. Try moving to a brighter area and centering your face.";
      status = "warning";
    } else {
      message = "✅ Good! Lighting looks fine. Ensure only your face is in the frame and centered.";
      status = "good";
    }

    setValidationMessage(message);
    setValidationStatus(status);
  }, [cameraReady]);

  // Run validation on video frames
  useEffect(() => {
    if (!cameraReady || imgSrc) {
      setValidationMessage("");
      setValidationStatus("");
      return;
    }

    let interval = null;
    
    // Small delay before starting validation to let camera stabilize
    const timeout = setTimeout(() => {
      interval = setInterval(() => {
        analyzeFrame();
      }, 500); // Check every 500ms
    }, 1000);

    return () => {
      clearTimeout(timeout);
      if (interval) clearInterval(interval);
    };
  }, [cameraReady, imgSrc, analyzeFrame]);


  const capture = useCallback(() => {
    if (!cameraReady) return;
    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) return;
    setImgSrc(imageSrc);
  }, [cameraReady]);

  const handleUpload = async () => {
    if (!imgSrc) return;
    setLoading(true);
    setError("");

    try {
      await api.post("/face/register", {
        user_id: userId,
        user_type: userType,
        image_b64: imgSrc.split(",")[1],
      });

      localStorage.setItem("face_id", "PRESENT");

      setToast({ type: "success", msg: "Face registered successfully" });

      // stop camera
      stopCamera();
      const stream = webcamRef.current?.video?.srcObject;
      if (stream) stream.getTracks().forEach((t) => t.stop());

      setTimeout(() => navigate("/student", { replace: true }), 1200);
    } catch (err) {
       const msg =
        err.response?.data?.detail ||err.response?.data?.message ||"Face registration failed";
        setToast({ type: "error", msg });
    }finally {
      setLoading(false);
    }
  };

  /* ================= UI ================= */
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white p-6">
      {/* TOAST */}
      {toast && (
        <div
          className={`fixed top-5 right-5 px-6 py-3 rounded-xl shadow-lg text-sm font-bold z-50 ${
            toast.type === "success"
              ? "bg-green-600"
              : "bg-red-600"
          }`}
        >
          {toast.msg}
        </div>
      )}

      <div className="max-w-md w-full bg-gray-800 p-8 rounded-3xl text-center">
        <h2 className="text-2xl font-bold mb-2">Biometric Enrollment</h2>
        <p className="text-gray-400 mb-4">
          Center your face and ensure good lighting
        </p>

        {error && (
          <div className="bg-red-600/20 text-red-400 p-3 rounded-xl mb-4">
            {error}
          </div>
        )}

        {permission === "denied" && (
          <button
            onClick={() =>
              alert(
                "Go to browser address bar → 🔒 → Site settings → Allow Camera → Reload"
              )
            }
            className="w-full py-3 bg-red-600 rounded-xl font-bold"
          >
            How to Enable Camera
          </button>
        )}

        {permission === "prompt" && (
          <button
            onClick={requestCamera}
            className="w-full py-4 bg-indigo-600 rounded-xl font-bold mb-4"
          >
            Enable Camera
          </button>
        )}

        {permission === "granted" && (
          <>
            <div className="aspect-square rounded-2xl overflow-hidden border-4 border-indigo-500 mb-4 relative">
              {!imgSrc ? (
                <>
                  <Webcam
                    ref={webcamRef}
                    audio={false}
                    screenshotFormat="image/jpeg"
                    videoConstraints={{ facingMode: "user" }}
                    onUserMedia={() => setCameraReady(true)}
                    className="w-full h-full object-cover"
                  />
                  {/* Hidden canvas for analysis */}
                  <canvas ref={canvasRef} className="hidden" />
                  {/* Live validation message overlay */}
                  {validationMessage && (
                    <div className={`absolute bottom-0 left-0 right-0 p-3 text-sm font-semibold ${
                      validationStatus === "good" 
                        ? "bg-green-600/90 text-white" 
                        : validationStatus === "warning"
                        ? "bg-yellow-600/90 text-white"
                        : "bg-red-600/90 text-white"
                    }`}>
                      {validationMessage}
                    </div>
                  )}
                </>
              ) : (
                <img src={imgSrc} className="w-full h-full object-cover" />
              )}
            </div>

            {!imgSrc ? (
              <div>
                <button
                  onClick={capture}
                  className={`w-full py-4 rounded-xl font-bold ${
                    validationStatus === "warning"
                      ? "bg-yellow-600 hover:bg-yellow-700"
                      : "bg-indigo-600 hover:bg-indigo-700"
                  }`}
                >
                  Capture
                </button>
              </div>
            ) : (
              <div className="flex gap-4">
                <button
                  onClick={() => setImgSrc(null)}
                  className="w-1/2 py-3 bg-gray-600 rounded-xl"
                >
                  Retake
                </button>
                <button
                  onClick={handleUpload}
                  disabled={loading}
                  className={`w-1/2 py-3 rounded-xl font-bold ${
                    loading
                      ? "bg-green-400 cursor-not-allowed"
                      : "bg-green-600"
                  }`}
                >
                  {loading ? "Registering..." : "Submit"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
