from PIL import Image
from pyzbar.pyzbar import decode
from datetime import datetime, timedelta


# Function to decode time from QR code data
def TimeCodeToUnix(qr_data):
    timestamp_str = qr_data.split("oT")[1].split("oTD")[0]
    timezone_offset_str = qr_data.split("oTZ")[1].split("oTI")[0]
    dt = datetime.strptime(timestamp_str, "%y%m%d%H%M%S.%f")
    timezone_offset_minutes = int(timezone_offset_str)
    timezone_offset = timedelta(minutes=timezone_offset_minutes)
    utc_dt = dt - timezone_offset
    unix_time = int(utc_dt.timestamp())
    return unix_time
