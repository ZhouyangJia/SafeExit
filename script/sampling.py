httpd_file = open('httpd-4-1.env', 'r')
httpd_lines = httpd_file.readlines()
httpd_head = httpd_lines[0]
httpd_head = httpd_head.strip().split('\t')

# get config_cmd and workload_cmd from each sample
smaple_count = 0
smaple_total = len(httpd_lines[1:])
for httpd_line in httpd_lines[1:]:
	smaple_count += 1
	httpd_body = httpd_line.strip().split('\t')
	cfg_str = ''
	workload_str = ''
	# for each environment variable
	for i in range(len(httpd_head)):
		# workload variable
		if '-' in httpd_head[i]:
			if httpd_body[i] != 'yes' and httpd_body[i] != 'no':
				workload_str += ' '+httpd_head[i]+' '+httpd_body[i]
			if httpd_body[i] == 'yes':
				workload_str += ' '+httpd_head[i]
		# config variable
		else:
			cfg_str += ' -c "'+httpd_head[i]+' '+httpd_body[i]+'"'
	config_cmd = '/usr/local/httpd/bin/httpd' + cfg_str
	workload_cmd = '/usr/local/httpd/bin/ab' + workload_str + \
		' 192.168.115.132:8080/'
	stop_cmd = '/usr/local/httpd/bin/httpd -k stop'

	print 'Case [%d/%d]'%(smaple_count, smaple_total)
	print config_cmd
	print workload_cmd
	print stop_cmd
	print