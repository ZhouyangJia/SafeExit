import random

var_name = []
var_value = []

#config variable
var_name.append('accessibility.AOM.enabled')
var_name.append('accessibility.tabfocus_applies_to_xul')
var_name.append('alerts.showFavicons')
var_name.append('app.update.cert.checkAttributes')
var_name.append('apz.allow_checkerboarding')
var_name.append('apz.disable_for_scroll_linked_effects')
var_name.append('apz.minimap.visibility.enabled')
var_name.append('apz.record_checkerboarding')
var_name.append('autocomplete.ungrab_during_mode_switch')
var_name.append('bidi.edit.delete_immediately')
var_name.append('browser.cache.disk.enable')
var_name.append('browser.cache.disk.smart_size.first_run')
var_name.append('browser.chrome.site_icons')
var_name.append('browser.display.force_inline_alttext')
var_name.append('browser.download.manager.addToRecentDocs')
var_name.append('browser.download.manager.showAlertOnComplete')
var_name.append('browser.fixup.dns_first_for_single_words')
var_name.append('browser.formfill.saveHttpsForms')
var_name.append('browser.meta_refresh_when_inactive.disabled')
var_name.append('browser.safebrowsing.downloads.remote.enabled')
var_name.append('browser.search.log')
var_name.append('browser.search.update')
var_name.append('browser.triple_click_selects_paragraph')
var_name.append('camera.control.face_detection.enabled')
var_name.append('canvas.imagebitmap_extensions.enabled')
var_name.append('chat.irc.automaticList')
var_name.append('clipboard.plainTextOnly')
var_name.append('datareporting.policy.dataSubmissionPolicyBypassNotification')
var_name.append('devtools.browserconsole.filter.info')
var_name.append('devtools.browserconsole.filter.serverinfo')
var_name.append('devtools.browserconsole.filter.sharedworkers')
var_name.append('devtools.chrome.enabled')
var_name.append('devtools.command-button-screenshot.enabled')
var_name.append('devtools.debugger.enabled')
var_name.append('devtools.debugger.remote-websocket')
var_name.append('extensions.getAddons.databaseSchema')
var_name.append('extensions.databaseSchema')
var_name.append('mail.server.server1.authMethod')
var_name.append('mail.smtpserver.smtp1.authMethod')
var_name.append('mail.server.server1.socketType')

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
var_value.append(['true', 'false'])
var_value.append(range(1, 6))
var_value.append(range(1, 20))
var_value.append(range(1, 11))
var_value.append(range(1, 11))
var_value.append(range(1, 4))

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
