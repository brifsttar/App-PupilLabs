import os

import pyxdf
import ffmpeg
from PIL import Image, ImageDraw
import numpy as np

GAZE_CIRCLE_RADIUS = 20
GAZE_CIRCLE_WIDTH = 2


def pupil_rebuild_video(xdf_file: str, draw_gaze: bool = True) -> None:
    g = GAZE_CIRCLE_RADIUS
    xdf_dir = os.path.dirname(xdf_file)
    data, header = pyxdf.load_xdf(xdf_file)

    # Loading video stream
    for stream in data:
        if stream['info']['name'][0] == 'pupil_capture_video':
            frames = stream['time_series']
            frames_ts = stream['time_stamps']
            video_path = stream['info']['desc'][0]['video_path'][0]
            fps = ((frames[-1] - frames[0]) / (frames_ts[-1] - frames_ts[0])).flat[0]
            break
    else:
        raise Exception("No Pupil video found in XDF data file")
    if draw_gaze:
        # Loading gaze stream
        for stream in data:
            if stream['info']['name'][0] == 'pupil_capture' and stream['info']['type'][0] == 'Gaze':
                gazes = stream['time_series']
                gazes_ts = stream['time_stamps']
                break
        else:
            raise Exception("No Pupil Gaze data found in XDF data file to draw gaze overlay")

    input_fn = os.path.join(xdf_dir, "inputs.txt")
    output_fn = os.path.join(xdf_dir, "pupil_scene_video.mp4")

    # Writing concat file for FFmpeg
    with open(input_fn, "w+") as f:
        for frame, timestamp in zip(frames, frames_ts):
            base_fp = os.path.join(video_path, str(frame.flat[0]))
            fp = base_fp + ".jpg"
            if draw_gaze:
                # Finding closest gaze data to frame
                idx = (np.abs(gazes_ts - timestamp)).argmin()
                gaze = gazes[idx].flat
                # Get its gaze coords
                norm_x, norm_y = gaze[1], gaze[2]
                img = Image.open(fp)
                w, h = img.size
                # Scale coords to image
                x = norm_x * w
                y = (1 - norm_y) * h
                # Draw circle
                draw = ImageDraw.Draw(img)
                gaze_box = (x - g, y - g, x + g, y + g)
                draw.ellipse(gaze_box, outline='red', width=GAZE_CIRCLE_WIDTH)
                # Save new image
                fp = base_fp + "_gaze.jpg"
                img.save(fp)
            # FFmpeg wants forward slashes
            fp = fp.replace('\\', '/')
            f.write(f"file '{fp}'\n")

    (
        ffmpeg
        .input(input_fn, format='concat', safe=0)
        .filter('fps', fps=fps, round='up')
        .output(output_fn, vcodec="mjpeg", **{'q:v': '2'})
        .overwrite_output()
        .run()
    )

    os.remove(input_fn)

