import os

import pyxdf
import ffmpeg


def pupil_rebuild_video(xdf_file: str) -> None:
    xdf_dir = os.path.dirname(xdf_file)
    data, header = pyxdf.load_xdf(xdf_file)
    for stream in data:
        if stream['info']['name'][0] == 'pupil_capture_video':
            break
    else:
        raise Exception("No Pupil video found in XDF data file")

    video_data = stream
    video_path = video_data['info']['desc'][0]['video_path'][0]
    frames = video_data['time_series']
    ts = video_data['time_stamps']
    fps = ((frames[-1] - frames[0]) / (ts[-1] - ts[0])).flat[0]
    input_fn = os.path.join(xdf_dir, "inputs.txt")
    output_fn = os.path.join(xdf_dir, "pupil_scene_video.mp4")

    with open(input_fn, "w+") as f:
        for frame in frames.flat:
            fp = os.path.join(video_path, str(frame)).replace('\\', '/')
            f.write(f"file '{fp}.jpg'\n")

    (
        ffmpeg
        .input(input_fn, format='concat', safe=0)
        .filter('fps', fps=fps, round='up')
        .output(output_fn, vcodec="mjpeg", **{'q:v': '2'})
        .overwrite_output()
        .run()
    )

    os.remove(input_fn)

