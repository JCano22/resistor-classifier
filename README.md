# Resistor Classifier

Captures labeled photos of electronic components (resistors, capacitors) with a USB
webcam on an Arduino UNO Q, to build a dataset for training an edge-AI image
classifier. Photos are synced to a Mac automatically while you capture.

```
 UNO Q (Board22)                                   Mac
 ┌──────────────────────────────┐   rsync (2 s)   ┌──────────────────────────────┐
 │ capture.py → captures/<label>│ ──────────────► │ uno_captures/<label>         │
 │            → captures/latest │                 │ capture-viewer (browser UI)  │
 └──────────────────────────────┘                 └──────────────────────────────┘
```

## Hardware

| Part | Details |
|---|---|
| Board | Arduino UNO Q (Linux side, hostname `Board22`) |
| Camera | Logitech HD Pro Webcam C920 (USB) |
| Setup | Camera pointing down at the component on plain white paper |

## Files

| File | Purpose |
|---|---|
| `capture.py` | Opens the camera, takes photos, saves them into a folder named after the label |
| `camera_test.py` | Tries `/dev/video0`–`3` and reports which ones return a frame |
| `captures/` | Output images (one subfolder per label, plus `latest.jpg`) |

## Setup (on the board)

```bash
cd ~/resistor_classifier
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Tested with Python 3.13. Exact package versions are pinned in `requirements.txt`.

## Capturing images

```bash
source venv/bin/activate
python3 capture.py <resistor|capacitor|test>
```

Each image is saved as:

```
captures/<label>/<label>_<YYYYMMDD>_<HHMMSS>_<n>.jpg
captures/latest.jpg          ← copy of the most recent image
```

Settings at the top of `capture.py`:

| Variable | Meaning |
|---|---|
| `numCaptures` | Photos per run |
| `delayTime` | Seconds between photos (time to reposition the component) |
| `CAMERA_DEVICE` | Stable path to the camera (see below) |

Images are 1920×1080 (MJPG). The script throws away the first 10 frames so
exposure can settle.

> ⚠️ **Each run deletes the label's folder on the board** (`shutil.rmtree`)
> before capturing. Photos survive only because the rsync loop copies them to
> the Mac first. **Keep `watchuno` running whenever you capture.**

### Why the camera is opened through `/dev/v4l/by-id/...`

Linux numbers video devices in the order it detects them, so the C920 can be
`/dev/video0` one time and `/dev/video2` another (the board's built-in Qualcomm
video decoder also takes two numbers). `/dev/v4l/by-id/` holds a symbolic link
named after the camera's model and serial number. Linux updates it to point at
whichever `/dev/videoN` the camera got.

OpenCV's V4L2 backend can't open a device by path, so `capture.py` follows the
link with `os.path.realpath()` and passes the number to OpenCV.

```bash
ls -l /dev/v4l/by-id/       # where the camera link points right now
v4l2-ctl --list-devices     # every video device and its name
```

A different C920 has a different serial number, so update `CAMERA_DEVICE` if
you swap cameras. Always use the `video-index0` link (`index1` is a metadata
stream, not images).

## Camera settings

The C920's focus, white balance, exposure, and zoom are set with `v4l2-ctl`.
Locked settings matter for training: auto white balance and autofocus change
from shot to shot, so the same band color can look different in two photos.
Use the **same settings for training captures and for running the model**.

```bash
CAM=/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_33B397DF-video-index0

# Focus: autofocus off, then manual (0 = far, 250 = closest ≈ 3 in, step 5)
v4l2-ctl -d $CAM -c focus_automatic_continuous=0
v4l2-ctl -d $CAM -c focus_absolute=140

# White balance: auto off, then fixed temperature (2000–6500 K)
#   lower = bluer picture, higher = warmer/more orange
v4l2-ctl -d $CAM -c white_balance_automatic=0
v4l2-ctl -d $CAM -c white_balance_temperature=4500

# Digital zoom (100 = none, 500 = 5×). Only crops the center, so it adds no detail.
v4l2-ctl -d $CAM -c zoom_absolute=100

# Check current values
v4l2-ctl -d $CAM -C focus_absolute,white_balance_temperature,zoom_absolute,gain
v4l2-ctl -d $CAM --list-ctrls      # all controls with min/max ranges
```

Current values for the white-paper setup:

| Control | Value |
|---|---|
| `focus_automatic_continuous` | 0 (off) |
| `focus_absolute` | 140 |
| `white_balance_automatic` | 0 (off) |
| `white_balance_temperature` | 4500 |
| `zoom_absolute` | 100 |

> **These settings reset when the camera is unplugged or the board reboots.**
> Run the commands above again before capturing.

Tips:
- Moving the camera closer gives more detail than digital zoom.
- If focus 250 is still blurry, the camera is closer than about 3 in. Raise it.
- `gain` is at its maximum of 255 when the scene is dark, which makes grainy images.
  More even, diffuse light on the paper brings it down.

## Syncing to the Mac (rsync)

On the Mac, this alias in `~/.zshrc` copies the board's `captures/` folder to the
Mac every 2 seconds:

```bash
alias watchuno='while true; do rsync -a --out-format="synced %n" arduino@Board22.local:~/resistor_classifier/captures/ "/Users/jorgecano/Documents/Personal/Projects/Edge Ai Resistor Classifier V1/uno_captures/"; sleep 2; done'
```

| Part | Meaning |
|---|---|
| `while true; …; sleep 2; done` | Repeat forever, every 2 seconds |
| `-a` | Archive mode: include subfolders and keep file timestamps |
| `--out-format="synced %n"` | Print each file name as it is copied |
| `…/captures/` (trailing `/`) | Copy what's **inside** `captures/`, not the folder itself |
| no `--delete` | Files deleted on the board are **kept** on the Mac |

Use it:

```bash
source ~/.zshrc     # after editing the alias
watchuno            # start syncing; Ctrl+C to stop
```

Notes:
- **Never add `--delete`.** Because `capture.py` wipes the label folder on every
  run, `--delete` would also erase the Mac copies.
- Sync the whole `captures/` folder, not `captures/test/`. Otherwise the other
  labels and `latest.jpg` never reach the Mac.
- Copying needs SSH access to `arduino@Board22.local`. Set up an SSH key to avoid
  being asked for a password every 2 seconds.

## Viewing captures (Mac)

A separate project, `capture-viewer`, is a small C web server on port 8080.
It serves a page that lists everything in `uno_captures/`, grouped by label
(`latest.jpg` appears under **Latest**), and refreshes every second. Leave it
open while you adjust focus or white balance to see each new capture.

## Known issues / to do

- `capture.py` deletes `captures/<label>/` on every run (see warning above).
- Camera settings aren't applied by `capture.py`, so they reset on unplug or reboot.
- High gain (255) adds noise. Improve the lighting.
- `capture.py` prints `Using camera/dev/video0` (missing space).
- In `capture-viewer`, thumbnails use a 4:3 crop but captures are now 16:9.
- Train the classifier.
