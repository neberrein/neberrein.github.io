"""Crop RViz UI and annotate visible BlueROV2 motion without changing telemetry.

Requires OpenCV, numpy, and imageio-ffmpeg (may be installed under .work/media-deps).
Arrows show displacement in screen coordinates, not vehicle yaw or commanded velocity.
Original published recordings remain untouched.
"""
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.work/media-deps'))
import imageio_ffmpeg

VIDEO = ROOT / 'dist/assets/videos'
IMAGE = ROOT / 'dist/assets/images'
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def encoder(destination, width, height, fps):
    return subprocess.Popen([
        FFMPEG, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', f'{width}x{height}', '-r', str(fps), '-i', 'pipe:0', '-an',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(destination),
    ], stdin=subprocess.PIPE)


def visible_rov(frame):
    hsv = cv2.cvtColor(frame[:, :950], cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([80, 70, 100]), np.array([115, 255, 255]))
    contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    contours = [c for c in contours if cv2.contourArea(c) > 15]
    if not contours:
        raise ValueError('BlueROV2 not visibly identifiable; annotation must be reviewed')
    centers = []
    for contour in contours:
        moment = cv2.moments(contour)
        centers.append((moment['m10'] / moment['m00'], moment['m01'] / moment['m00']))
    centers = np.array(centers)
    weights = np.array([cv2.contourArea(c) for c in contours])
    anchor = centers[weights.argmax()]
    nearby = np.linalg.norm(centers - anchor, axis=1) < 45
    return np.average(centers[nearby], weights=weights[nearby], axis=0)


def annotate_gazebo():
    source = VIDEO / 'manta-gazebo-avoidance.mp4'
    capture = cv2.VideoCapture(str(source))
    fps = capture.get(cv2.CAP_PROP_FPS)
    positions = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        positions.append(visible_rov(frame))
    capture.release()
    positions = np.array(positions)
    # Average frame-level detections to suppress tiny shifts within the four thrusters.
    smooth = np.array([positions[max(0, i-3):i+4].mean(axis=0) for i in range(len(positions))])
    capture = cv2.VideoCapture(str(source))
    output = encoder(VIDEO / 'manta-gazebo-motion-annotated.mp4', 1280, 720, fps)
    cyan = (255, 224, 32)
    for i, center in enumerate(smooth):
        ok, frame = capture.read()
        if not ok:
            raise ValueError('Source recording ended unexpectedly')
        before = smooth[max(0, i-8)]
        after = smooth[min(len(smooth)-1, i+8)]
        delta = after - before
        distance = np.linalg.norm(delta)
        point = tuple(np.rint(center).astype(int))
        cv2.circle(frame, point, 19, (12, 24, 38), 5, cv2.LINE_AA)
        cv2.circle(frame, point, 19, cyan, 2, cv2.LINE_AA)
        if distance > 3:
            direction = delta / distance
            start = tuple(np.rint(center + direction * 24).astype(int))
            end = tuple(np.rint(center + direction * 94).astype(int))
            cv2.arrowedLine(frame, start, end, (12, 24, 38), 9, cv2.LINE_AA, tipLength=.25)
            cv2.arrowedLine(frame, start, end, cyan, 5, cv2.LINE_AA, tipLength=.25)
        x, y = max(5, point[0]-48), max(28, point[1]-32)
        cv2.rectangle(frame, (x-5, y-24), (x+108, y+6), (12, 24, 38), -1)
        cv2.putText(frame, 'BlueROV2', (x, y), cv2.FONT_HERSHEY_SIMPLEX, .62,
                    (255, 255, 255), 2, cv2.LINE_AA)
        output.stdin.write(frame.tobytes())
        if i == round(fps * 13):
            cv2.imencode('.jpg', frame)[1].tofile(str(IMAGE / 'manta-gazebo-motion-preview.jpg'))
    capture.release()
    output.stdin.close()
    if output.wait() != 0:
        raise RuntimeError('Gazebo encoding failed')
    print('Gazebo annotated:', len(smooth), 'frames at', fps, 'fps')


def crop_rviz():
    capture = cv2.VideoCapture(str(VIDEO / 'manta-rviz-implementation.mp4'))
    fps = capture.get(cv2.CAP_PROP_FPS)
    output = encoder(VIDEO / 'manta-rviz-path-only.mp4', 718, 574, fps)
    count = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame.shape[:2] != (720, 1280):
            raise ValueError('RViz source layout changed; crop requires review')
        # Render viewport only: no title bar, toolbar, Displays, Views or status bar.
        viewport = frame[102:676, 492:1210].copy()
        output.stdin.write(viewport.tobytes())
        if count == round(fps * 26):
            cv2.imencode('.jpg', viewport)[1].tofile(str(IMAGE / 'manta-rviz-path-preview.jpg'))
        count += 1
    capture.release()
    output.stdin.close()
    if output.wait() != 0:
        raise RuntimeError('RViz encoding failed')
    print('RViz cropped:', count, 'frames at', fps, 'fps')


if __name__ == '__main__':
    annotate_gazebo()
    crop_rviz()
