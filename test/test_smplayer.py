import random

var_name = []
var_value = []

#config variable
var_name.append('add_blackborders_on_fullscreen=false')
var_name.append('autoload_m4a=true')
var_name.append('autosync=false')
var_name.append('disable_screensaver=true')
var_name.append('dont_remember_media_settings=false')
var_name.append('dont_remember_time_pos=false')
var_name.append('global_audio_equalizer=true')
var_name.append('global_volume=true')
var_name.append('remember_media_settings=true')
var_name.append('remember_stream_settings=true')
var_name.append('remember_time_pos=true')
var_name.append('tablet_mode=false')
var_name.append('use_audio_equalizer=false')
var_name.append('use_direct_rendering=false')
var_name.append('use_double_buffer=true')
var_name.append('use_hwac3=false')
var_name.append('use_mc=false')
var_name.append('use_soft_video_eq=false')
var_name.append('use_soft_vol=true')
var_name.append('vdpau_disable_video_filters=true')
var_name.append('vdpau_ffh264vdpau=true')
var_name.append('vdpau_ffhevcvdpau=false')
var_name.append('vdpau_ffmpeg12vdpau=true')
var_name.append('repaint_video_background=false')
var_name.append('save_smplayer_log=false')
var_name.append('show_tag_in_window_title=true')
var_name.append('fullscreen_playlist_was_visible=false')
var_name.append('ignore_playlist_events=false')
var_name.append('mainwindow_visible=true')
var_name.append('format_info=false')
var_name.append('frame_counter=false')
var_name.append('fullscreen_toolbar1_was_visible=false')
var_name.append('play_files_from_start=true')
var_name.append('recursive_add_directory=false')
var_name.append('recents\\max_items=10')
var_name.append('urls\\max_items=50')
var_name.append('initial_sub_pos=100')
var_name.append('initial_sub_scale=5')

#config variable value
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(['true', 'false'])
var_value.append(range(1, 11))
var_value.append(range(1, 51))
var_value.append(range(1, 101))
var_value.append(range(1, 6))

name_str = ''
for i in range(len(var_name)):
	name = var_name[i]
	name_str += name+'\t'
print name_str.strip()

cnt = 100
while cnt:
	values = []
	for i in range(len(var_value)):
		values.append(random.choice(var_value[i]))

	value_str = ''
	for value in values:
		value_str += str(value)+'\t'
	print value_str.strip()
	cnt -= 1;
