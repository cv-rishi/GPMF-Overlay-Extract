# This is a script based on [this npm package](https://www.npmjs.com/package/gpmf-extract) and this [this gopro overlay repository](https://github.com/time4tea/gopro-dashboard-overlay)

## Extracting GPMF data from GoPro videos, and overlaying it on the video.

## Requirements

### Binaries

- Node.js
- npm
- ffmpeg
- Python 3.6+

### Python packages

- libraqm (needed by [Pillow](https://pypi.org/project/Pillow/))
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

- [gopro-dashboard-overlay](https://github.com/time4tea/gopro-dashboard-overlay) to use ACCL, GRYO, and CORI data. [weird bug, they weren't loading, something about checking if a set was empty but it was not]
