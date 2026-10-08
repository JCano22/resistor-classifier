import cv2
import os, shutil, sys
import time

CAMERA_DEVICE = '/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_33B397DF-video-index0'
numCaptures = 1
delayTime = 2

if len(sys.argv) < 2:
    raise SystemExit("Usage: python capture.py <resistor|capacitor|test>")
    
if sys.argv[1] == 'resistor':
    label = 'resistor'
elif sys.argv[1] == 'capacitor':
    label = 'capacitor'
elif sys.argv[1] == 'test':
    label = 'test'
else:
    raise SystemExit(f"Unknown label {sys.argv[1]}")

CAPTURE_ROOT = os.path.expanduser('~/resistor_classifier/captures')

def write_atomic(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)

saveDir = os.path.join(CAPTURE_ROOT, label)
shutil.rmtree(saveDir, ignore_errors=True)
os.makedirs(saveDir, exist_ok=True)

cameraPath = os.path.realpath(CAMERA_DEVICE)
cameraIndex = int(cameraPath.replace('/dev/video', ''))
print(f"Using camera{cameraPath}")
cap = cv2.VideoCapture(cameraIndex, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
if not cap.isOpened():
    raise SystemExit(f"Could not open {CAMERA_DEVICE}")

for _ in range(10):     #let auto-exposure settle; first frames are often dark
    cap.read()

for i in range(numCaptures):
    ok, frame = cap.read()
    if ok:
        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if ok:
        imageBytes = jpeg.tobytes()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(saveDir, f"{label}_{timestamp}_{i+1}.jpg")
        with open(filename, "wb") as f:
            f.write(imageBytes)
        write_atomic(os.path.join(CAPTURE_ROOT, 'latest.jpg'), imageBytes)
        print(f"Saved {filename}.")
    else:
        print("Frame capture failed, skipping.")
    time.sleep(delayTime)

cap.release()
