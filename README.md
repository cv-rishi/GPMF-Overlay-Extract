# This is a script based on [this npm package](https://www.npmjs.com/package/gpmf-extract) and this [this gopro overlay repository](https://github.com/time4tea/gopro-dashboard-overlay)

## Extracting GPMF data from GoPro videos, and overlaying it on the video.

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

### Changes

- [gopro-dashboard-overlay](https://github.com/time4tea/gopro-dashboard-overlay) to use ACCL, GRYO, and CORI data. [weird bug, they weren't loading, something about checking if a set was empty but it was not]
