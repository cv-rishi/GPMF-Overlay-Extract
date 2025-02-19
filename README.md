# This is a script based on [this npm package](https://www.npmjs.com/package/gpmf-extract) and this [this gopro overlay repository](https://github.com/time4tea/gopro-dashboard-overlay)

# Syncing multiple videos, and normalizing them to be 10 minutes long and if we have a gorpo video we are Exracting the sensor data.

## Usage

```shell
python Generate.py \
    --front_videos \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/Front_View/Day1_3-2-25_Morning/GX010406.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/Front_View/Day1_3-2-25_Morning/GX020406.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/Front_View/Day1_3-2-25_Morning/GX030406.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/Front_View/Day1_3-2-25_Morning/GX040406.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/Front_View/Day1_3-2-25_Morning/GX050406.MP4 \
    --back_videos \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/HelmetView/Day1_Helmet_morning/GX010404.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/HelmetView/Day1_Helmet_morning/GX020404.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/HelmetView/Day1_Helmet_morning/GX030404.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/HelmetView/Day1_Helmet_morning/GX040404.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/HelmetView/Day1_Helmet_morning/GX050404.MP4 \
    --helmet_videos \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/RearView/Day1_Rear_morning/GX010406.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/RearView/Day1_Rear_morning/GX020406.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/RearView/Day1_Rear_morning/GX030406.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/RearView/Day1_Rear_morning/GX040406.MP4 \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/RearView/Day1_Rear_morning/GX050406.MP4 \
    --glasses_video \
    /media/teddy-bear/Extreme\ SSD/2W\ -\ Data_Capture/Day1_03_02_2025/AriaView/Aria_data/azhar0302205.mp4 \
    --driver_name "Morning"
    --output output
```

## Requirements

### Binaries

- Node.js
- npm
- ffmpeg
- Python 3.6+

### Python packages

- Install the requirements in the `requirements.txt` file.
  - `pip install -r requirements.txt`

### Node packages

- Install the requirements in the `package.json` file.
  - `npm install`

The Roboto font needs to be installed on your system. You could install it with one of the following commands maybe.

```bash
pacman -S ttf-roboto
apt install truetype-roboto
apt install fonts-roboto
```

#### (Optional) Installing pycairo

Optionally, install `pycairo`

```shell
venv/bin/pip install pycairo==1.23.0
```

You might need to install some system libraries - This is what the pycairo docs suggest:

Ubuntu/Debian: `sudo apt install libcairo2-dev pkg-config python3-dev`

macOS/Homebrew: `brew install cairo pkg-config`

### Changes

- [gopro-dashboard-overlay](https://github.com/time4tea/gopro-dashboard-overlay) to use ACCL, GRYO, and CORI data. (weird bug, they weren't loading, something about checking if a set was empty but it was not)
