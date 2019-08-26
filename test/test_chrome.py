import random

var_name = []
var_value = []

#config variable
var_name.append('--agc-startup-min-volume')
var_name.append('c1')
var_name.append('c2')
var_name.append('c4')
var_name.append('c5')
var_name.append('--alsa-enable-upsampling')
var_name.append('c7')
var_name.append('c8')
var_name.append('c9')
var_name.append('c10')
var_name.append('c11')
var_name.append('c12')
var_name.append('--audio-output-channels')
var_name.append('c14')
var_name.append('c15')
var_name.append('c16')
var_name.append('c17')
var_name.append('c19')
var_name.append('c20')
var_name.append('c21')
var_name.append('c22')
var_name.append('c23')
var_name.append('c24')
var_name.append('c25')
var_name.append('c26')
var_name.append('c27')
var_name.append('c28')
var_name.append('c29')
var_name.append('c30')
var_name.append('c31')
var_name.append('c32')
var_name.append('c33')
var_name.append('c34')
var_name.append('c35')
var_name.append('--data-reduction-proxy-lo-fi')

#config variable value
var_value.append(range(12, 256))
var_value.append(['--accept-resource-provider', ''])
var_value.append(['--account-consistency', ''])
var_value.append(['--allow-cross-origin-auth-prompt', ''])
var_value.append(['--allow-hidden-media-playback', ''])
var_value.append(['32kHz', '48kHz'])
var_value.append(['--alternative', ''])
var_value.append(['--app', ''])
var_value.append(['--arc-availability=installed', ''])
var_value.append(['--ash-animate-from-boot-splash-screen', ''])
var_value.append(['--ash-enable-magnifier-key-scroller', ''])
var_value.append(['--ash-enable-night-light', ''])
var_value.append(range(1, 11))
var_value.append(['--auto', ''])
var_value.append(['--bwsi', ''])
var_value.append(['--ChromeOSMemoryPressureHandling', ''])
var_value.append(['--cloud-print-setup-proxy', ''])
var_value.append(['--disable-2d-canvas-clip-aa', ''])
var_value.append(['--disable-backing-store-limit', ''])
var_value.append(['--disable-direct-composition-layers', ''])
var_value.append(['--disable-hang-monitor', ''])
var_value.append(['--disable-local-storage', ''])
var_value.append(['--disable-per-user-timezone', ''])
var_value.append(['--disable-permission-action-reporting', ''])
var_value.append(['--disable-suggestions-ui', ''])
var_value.append(['--disable-sync', ''])
var_value.append(['--enable-accelerated-2d-canvas', ''])
var_value.append(['--enable-cast-receiver', ''])
var_value.append(['--fast-start', ''])
var_value.append(['--force-enable-stylus-tools', ''])
var_value.append(['--force-first-run', ''])
var_value.append(['--incognito', ''])
var_value.append(['--is-running-in-mash', ''])
var_value.append(['--log-net-log', ''])
var_value.append(['always-on', 'cellular-only', 'disabled'])

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
