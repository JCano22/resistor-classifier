import cv2

for index in range(4):
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"/dev/video{index}: could not open")
        continue
    ok, frame = cap.read()
    if ok:
        print(f"/dev/video{index}: WORKS, frame size {frame.shape[1]}x{frame.shape[0]}")
    else:
        print(f"/dev/video{index}: opened but no frame")
    cap.release()
