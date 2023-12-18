def edit_video(original_video_location: str, s3):
    # requested edit settings stored in json obj
    # assumed video has already been pulled into local dir 
    # upload to s3 after processing with ffmpeg engine
    try:
        path = original_video_location
        upload_location = original_video_location
        extension = path[path.rfind('.'):]
        duration = ffmpeg.probe(path)["format"]["duration"]
        zoom_settings = video_settings.get('zoom', [])
        start_time = video_settings.get('start', '00:00:00')
        end_time = video_settings.get('end', duration)
        input_path = path[0:path.rfind('.')] + '_before_edit' + '.' + path[path.rfind('.') + 1:]

        if (video_settings.get('start', 0) != 0 or video_settings.get('end', 0) != 0) and 'zoom' not in zoom_settings:
            # edit duration only
            shutil.copy(path, input_path)
            video = ffmpeg.input(input_path, ss=start_time, t=end_time)
            video = ffmpeg.output(video, path)
            video = ffmpeg.overwrite_output(video)
            ffmpeg.run(video)
            s3.upload_file(path, (upload_location + extension).__str__())
            os.remove(input_path)
        elif 'zoom' in zoom_settings:
            # full edit
            probe = ffmpeg.probe(path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)

            w = int(video_stream['width'])
            h = int(video_stream['height'])
            scale = zoom_settings['zoom']
            pct_move_x = float(zoom_settings['movePctX'])
            pct_move_y = float(zoom_settings['movePctY'])

            crop_w = (((scale * w - w) / 2) - (pct_move_x * w * scale))
            crop_h = (((scale * h - h) / 2) - (pct_move_y * h * scale))

            # print('width:', w, ' height:', h, ' zoom:', scale)
            # print('duration start: ', start_time, ' end: ', end_time)
            # print('crop points', crop_w, crop_h)
            shutil.copy(path, input_path)
            video = ffmpeg.input(input_path, ss=start_time, t=end_time)

            if zoom_settings['flip'] == '-':
                video = ffmpeg.hflip(video)
            if zoom_settings['rotate'] != 0:
                video = ffmpeg.vflip(video)
            if crop_w != 0 and crop_h != 0:
                # zoomed, x and y are moved
                video = ffmpeg.filter(video, 'scale', scale * w, scale * h)
                video = ffmpeg.filter(video, 'crop', w, h, crop_w, crop_h)
            elif crop_w != 0:
                # zoomed and moved only on x
                video = ffmpeg.filter(video, 'scale', scale * w, scale * h)
                video = ffmpeg.filter(video, 'crop', w, h, crop_w)
            elif crop_h != 0:
                # zoomed and moved only on y
                video = ffmpeg.filter(video, 'scale', scale * w, scale * h)
                video = ffmpeg.filter(video, 'crop', w, h, (scale * w - w) / 2, crop_h)
            elif scale > 1.0:
                # zoom in centered
                video = ffmpeg.filter(video, 'scale', scale * w, scale * h)
                video = ffmpeg.filter(video, 'crop', w, h)
            video = ffmpeg.output(video, path)
            video = ffmpeg.overwrite_output(video)
            ffmpeg.run(video)
            s3.upload_file(path, (upload_location + extension).__str__())
            os.remove(input_path)
    except BaseException as e:
        print("Error editing video " + e.__str__())
        return {
            "details": "Could not edit video"
        }
