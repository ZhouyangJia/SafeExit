import os
import sys
import time
import getopt
import datetime
import ConfigParser
import subprocess
import psutil
from shutil import copyfile


# usage of this script
def usage():
	print '%s: test programs by signals and generate trace files'%sys.argv[0]
	print 'Usage:'
	print '\tsudo python %s [-c <config_file.ini>]'%sys.argv[0],
	print '[-t <traces_dir>] [-s <sleep>] [-m <mode>] [-e <epoch>]'
	print '\tsudo python %s [-h]'%sys.argv[0]
	print 'Options:'
	print '\t-c specify the path to the config file'
	print '\t-t specify the path to the traces directory'
	print '\t-s sleep time between start, stop and clean commands'
	print '\t-m specify the test mode, \'normal\'/\'signal\''
	print '\t-e specify epoch, the running time for each testcase'
	print '\t-h print help messages'

long_domain = ['broswer', 'office']
long_project = ['mysql']

# helper function to map options to values in a given section
def config_section_map(section):
	config_dict = {}
	section_options = config.options(section)
	for option in section_options:
		if option == 'server' or option == 'root':
			config_dict[option] = config.getboolean(section, option)
		else:
			config_dict[option] = config.get(section, option)
	return config_dict


# helper function to change the ids for subprocesses only
def demote(user_uid, user_gid):
	def set_ids():
		os.setgid(user_gid)
		os.setuid(user_uid)
	return set_ids


# helper function to execute command and print if necessary
def run_cmd(cmd, root, log_file):
	print 'Command:',cmd
	log_file.write('\t'+get_timestamp()+' root:'+str(root)+' '+cmd+'\n')
	log_file.flush()
	if root:
		return subprocess.Popen('sudo '+cmd, shell=True)
	else:
		return subprocess.Popen(cmd, shell=True, preexec_fn=demote(1000, 1000))


# helper function to get current time stamp
def get_timestamp():
	return str(datetime.datetime.now())


# helper function to get pids of a given pid name list
def get_pid(name):
	ret = []
	try:
		ret += map(int,subprocess.check_output(["pgrep",name]).split())
	except Exception:
		pass
	ret.sort(reverse=True)
	return ret


# helper function to get children pids of a given pid
def pid_in_group(pid):
	proc = subprocess.Popen('ps -o pid,pgid -A | grep "%d"' % pid, shell=True,
							stdout=subprocess.PIPE)
	pid_pgid = [x.split() for x in proc.communicate()[0].split("\n") if x]
	return list(int(p) for p, pg in pid_pgid if int(pg) == pid)


# helper function to get thread tids of a given pid
def tid_in_group(pid):
	proc = subprocess.Popen('ps -To tid,pid "%d" | grep "%d"' % (pid, pid),
							shell=True, stdout=subprocess.PIPE)
	tid_pid = [x.split() for x in proc.communicate()[0].split("\n") if x]
	return list(int(t) for t, p in tid_pid if int(p) == pid)


# run test case
# case_info: domain, project, proc_name, testcase, config_cmd, \
# 				start_cmd, workload_cmd, stop_cmd, isroot, epoch
def run_case(case_info):

	[domain, project, proc_name, testcase, config_cmd, start_cmd, \
		workload_cmd, stop_cmd, isroot, epoch] = case_info

	# get the path to put the traces
	path = traces_dir+'/'+domain+'/'+project+'/'+testcase+'/'+mode+\
		'_epoch_'+str(epoch)

	# make dir if not exist
	mkdir_cmd = 'mkdir -p ' + path
	mkdir_proc = subprocess.Popen(mkdir_cmd, shell=True, \
		stdout=subprocess.PIPE, stderr=subprocess.STDOUT, \
		preexec_fn=demote(1000, 1000))
	ret = mkdir_proc.wait()
	if ret != 0:
		sys.stderr.write('Fail to make dir: %s\n' % path)
		for line in iter(mkdir_proc.stdout.readline, ''):
			print line,
		return

	# open log file
	log_path = path + '/' + 'runtime.log'
	log_file = open(log_path, 'w')

	# test different exit signals (from 0 to 15), 0 for normal exit
	signal_list = [0]
	if mode == 'signal':
		signal_list = [1, 2, 3, 4, 6, 7, 8, 9, 11, 13, 15, 24, 25] #range(1, 16)#
	for signal in signal_list:

		log_file.write('Signal: ' + str(signal) + '\n')
		log_file.flush()
		sys.stdout.write('Analyzing signal: %d\n' % signal)

		# stop project if running before testing (block)
		if signal == 0 and len(get_pid(proc_name)) != 0:
			stop_proc = run_cmd(stop_cmd, isroot, log_file)
			stop_proc.wait()
			time.sleep(sleep_time)
			if domain in long_domain or project in long_project:
				time.sleep(sleep_time * 3)

		# config project (block)
		if config_cmd != '':
			config_proc = run_cmd(config_cmd, isroot, log_file)
			config_proc.wait()
			time.sleep(sleep_time)

		# start project (non-block)
		if start_cmd != '':
			#strace_cmd = 'strace -i -tt -ff -yy -x -s 2000 -o '\
			#	+ path + '/' + str(signal) + ' '
			start_proc = run_cmd(start_cmd, isroot, log_file)
			time.sleep(sleep_time)
			if domain in long_domain or project in long_project:
				time.sleep(sleep_time * 3)

		# get the processes of the project (block)
		project_pids = get_pid(proc_name)
		if len(project_pids) == 0:
			sys.stderr.write('No process for command: %s\n' % start_cmd)
			exit(1)

		# trace processes (non-block)
		pid_str = ''
		for project_pid in project_pids:
			pid_str += str(project_pid)+','
		# -k -e trace=write,unlink,kill unlink,pwrite64,fsync,write,rename,exit_group
		#['rmdir', 'unlink', 'ftruncate', 'rename', 'open', 'openat', \
		#'creat', 'fsync', 'fdatasync', 'write', 'writev', 'pwrite64', 'fcntl', \
		#'sendmmsg', 'sendto', 'sendmsg', 'io_submit', 'execve', 'kill', \
		#'bind', 'flock', 'futex', 'mkdir', 'quotactl', 'exit_group', 'clone', \
		#'chown', 'fchown', 'link', 'msync', 'munlockall']
		strace_cmd = 'strace -i -tt -ff -yy -x -s 20 -e trace=rmdir,unlink,'+\
		'ftruncate,rename,open,openat,creat,fsync,fdatasync,write,writev,'+\
		'pwrite64,fcntl,sendmmsg,sendto,sendmsg,io_submit,execve,kill,bind,'+\
		'flock,futex,mkdir,quotactl,exit_group,clone,chown,fchown,link,msync,'+\
		'munlockall -o ' + path + '/' + str(signal) + ' '
		run_cmd(strace_cmd + '-p ' + str(pid_str), True, log_file)
		time.sleep(sleep_time)
		if domain in long_domain or project in long_project:
			time.sleep(sleep_time * 3)

		# get the relationship of processes and record (block)
		pid_pair_list = []
		for mpid in project_pids:
			try:
				mppid = psutil.Process(int(mpid)).ppid()
				pid_pair_list.append(str(mppid)+':'+str(mpid))
			except Exception:
				continue
		echo_str = str(pid_pair_list)
		my_proc = run_cmd('echo "pid ' + echo_str + '"', False, log_file)
		my_proc.wait()

		# get tid and record (block)
		tid_pair_list = []
		for mpid in project_pids:
			tid_list = tid_in_group(int(mpid))
			for tid in tid_list:
				tid_pair_list.append(str(mpid)+':'+str(tid))
		echo_str = str(tid_pair_list)
		my_proc = run_cmd('echo "tid ' + echo_str + '"', False, log_file)
		my_proc.wait()

		# get open file info and record (block)
		# this step is time comsuming, we only record for sample_0,
		# which means empty workload and default config.
		if testcase == 'sample_0':
			of_path = path + '/' + str(signal) + '.openfd.log'
			my_proc = run_cmd('lsof > '+of_path, True, log_file)
			my_proc.wait()

		# load workload (block)
		workload_time = get_timestamp()
		if workload_cmd != '':
			load_proc = run_cmd(workload_cmd, isroot, log_file)
			load_proc.wait()
			time.sleep(sleep_time)

		# stop project (block)
		stop_time = get_timestamp()
		if signal == 0:
			stop_root = False
			if 'sudo' in stop_cmd:
				stop_root = True
			stop_proc = run_cmd(stop_cmd, isroot | stop_root, log_file)
			stop_proc.wait()
		else:
			# the main process is supposed to be the last one of project_pids
			signal_cmd = 'kill -' + str(signal) + ' ' + str(project_pids[-1])
			signal_proc = run_cmd(signal_cmd, True, log_file)
			signal_proc.wait()
		time.sleep(sleep_time)

		# wait for normal stop
		if signal == 0:
			cnt = 0
			while True:
				cnt += 1
				# wait for *sleep_time* more seconds
				if len(get_pid(proc_name)) != 0:
					tmp_proc = run_cmd('echo "waiting ..."', False, log_file)
					tmp_proc.wait()
					time.sleep(sleep_time)
				else:
					break
				# give up waiting
				if cnt == 100:
					sys.stderr.write('Normal exit command unfinished!\n')
					exit(1)

		# record original and remained pids
		tmp_proc = run_cmd('echo "origin pid: '+str(project_pids)+'"', \
			False, log_file)
		tmp_proc.wait()
		remain_pids = get_pid(proc_name)
		tmp_proc = run_cmd('echo "remain pid: '+str(remain_pids)+'"', \
			False, log_file)
		tmp_proc.wait()

		# clean project
		# try normal exit first
		clean_time = get_timestamp()
		if signal != 0 and len(get_pid(proc_name)) != 0:
			stop_proc = run_cmd(stop_cmd, isroot, log_file)
			stop_proc.wait()
			time.sleep(sleep_time)
			if domain in long_domain or project in long_project:
				time.sleep(sleep_time * 3)

		# clean orphan processes
		remain_pids = get_pid(proc_name)
		remain_pids += project_pids
		kill_cnt = 0
		for pid in reversed(remain_pids):
			try:
				os.kill(pid, 0)
				clean_proc = run_cmd('kill -9 ' + str(pid), True, log_file)
				clean_proc.wait()
				kill_cnt += 1
			except Exception:
				continue
		if kill_cnt != 0:
			time.sleep(sleep_time)
			if domain in long_domain or project in long_project:
				time.sleep(sleep_time * 3)

		# restart the project to make webbrowsers and office happy
		if signal != 0:
			if domain == 'browser' or domain == 'office':
				restart_proc = run_cmd(start_cmd, isroot, log_file)
				time.sleep(sleep_time)
				if domain == 'office':
					tmp_cmd = 'xdotool key Return Return '
					restart_proc = run_cmd(tmp_cmd, isroot, log_file)
					time.sleep(3)
				restop_proc = run_cmd(stop_cmd, isroot, log_file)
				restop_proc.wait()
				time.sleep(sleep_time)
				if domain in long_domain or project in long_project:
					time.sleep(sleep_time * 3)

		# record time stamp
		log_file.write('\ttimestamp: ' + workload_time + ' ' + \
			stop_time + ' ' + clean_time + '\n')
		log_file.flush()
		sys.stdout.flush()

	# close log file
	log_file.close()


def do_testing():

	# parse config file
	global config
	if conf_file == '':
		sys.stderr.write('Please specify conf file!\n')
		usage()
		sys.exit(1)
	config = ConfigParser.ConfigParser()
	config.read(conf_file)

	# for each config section
	config_sections = config.sections()
	section_total = len(config_sections)
	section_count = 0
	for config_section in config_sections:
		section_count += 1

		# check config section
		for item in ['domain','project','name','start','stop','env','root']:
			if item not in config_section_map(config_section):
				sys.stderr.write('Invalid config file!\n')
				sys.exit(1)

		# get config options
		domain = config_section_map(config_section)['domain']
		project = config_section_map(config_section)['project']
		proc_name = config_section_map(config_section)['name']
		start_cmd = config_section_map(config_section)['start']
		stop_cmd = config_section_map(config_section)['stop']
		env_file = config_section_map(config_section)['env']
		isroot = config_section_map(config_section)['root']

		# print domain and project of current section
		sys.stdout.write('[%d/%d] ' % (section_count, section_total))
		sys.stdout.write('Domain: %s\tProject: %s\n' % (domain, project))

		# use empth workload and default config, run *epoch* times
		for i in range(epoch):
			sys.stdout.write('Epoch %d\tEmpth workload & default config\n'%(i))
			case_info = [domain, project, proc_name, 'sample_0', '', \
				start_cmd, '', stop_cmd, isroot, i]
			run_case(case_info)

		# use sampled workload and config, run *epoch* times for each
		# we need to decode the sampling file for each program

		# for httpd
		if os.path.isfile(env_file) and proc_name == 'httpd':
			httpd_file = open(env_file, 'r')
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
					' 127.0.0.1:8080/'
				# for each epoch
				for i in range(epoch):
					sys.stdout.write('Epoch %d\tSample[%d/%d]: %s\n' % (i, \
						smaple_count, smaple_total, httpd_line.strip()))
					sample_name = 'sample_' + str(smaple_count)
					# we use the config_cmd to start the server
					case_info = [domain, project, proc_name, sample_name, '', \
						config_cmd, workload_cmd, stop_cmd, isroot, i]
					run_case(case_info)
			httpd_file.close()

		# for mysql
		if os.path.isfile(env_file) and proc_name == 'mysqld':
			m_file = open(env_file, 'r')
			m_lines = m_file.readlines()
			m_head = m_lines[0]
			m_head = m_head.strip().split('\t')

			# get config_cmd and workload_cmd from each sample
			smaple_count = 0
			smaple_total = len(m_lines[1:])
			for m_line in m_lines[1:]:
				smaple_count += 1
				m_body = m_line.strip().split('\t')
				cfg_str = ''
				workload_str = ''
				# for each environment variable
				for i in range(len(m_head)):
					if i < 21:
						if m_head[i][0] == 'c':
							cfg_str += ' '+m_body[i]
						else:
							cfg_str += ' '+m_head[i]+'='+m_body[i]
					else:
						if m_head[i][0] == 'c':
							workload_str += ' '+m_body[i]
						else:
							workload_str += ' '+m_head[i]+'='+m_body[i]

				config_cmd = '/usr/local/mysql/bin/mysqld ' + cfg_str
				workload_cmd = '/usr/local/mysql/bin/mysqlslap --user=root ' + \
					workload_str + ' --auto-generate-sql --verbose'
				#print config_cmd
				#print workload_cmd
				#continue
				# for each epoch
				for i in range(epoch):
					sys.stdout.write('Epoch %d\tSample[%d/%d]: %s\n' % (i, \
						smaple_count, smaple_total, m_line.strip()))
					sample_name = 'sample_' + str(smaple_count)
					# we use the config_cmd to start the server
					case_info = [domain, project, proc_name, sample_name, '', \
						config_cmd, workload_cmd, stop_cmd, isroot, i]
					run_case(case_info)
			m_file.close()

		# for chrome
		if os.path.isfile(env_file) and proc_name == 'chromium-browse':
			m_file = open(env_file, 'r')
			m_lines = m_file.readlines()
			m_head = m_lines[0]
			m_head = m_head.strip().split('\t')

			# get config_cmd from each sample
			smaple_count = 0
			smaple_total = len(m_lines[1:])
			for m_line in m_lines[1:]:
				smaple_count += 1
				m_body = m_line.strip().split('\t')
				cfg_str = ''
				# for each environment variable
				for i in range(len(m_head)):
					if m_head[i][0] == 'c':
						cfg_str += ' '+m_body[i]
					else:
						cfg_str += ' '+m_head[i]+'='+m_body[i]

				config_cmd = 'chromium-browser ' + cfg_str
				#print config_cmd
				#continue
				# for each epoch
				for i in range(epoch):
					sys.stdout.write('Epoch %d\tSample[%d/%d]: %s\n' % (i, \
						smaple_count, smaple_total, m_line.strip()))
					sample_name = 'sample_' + str(smaple_count)
					# we use the config_cmd to start the server
					case_info = [domain, project, proc_name, sample_name, '', \
						config_cmd, '', stop_cmd, isroot, i]
					run_case(case_info)
			m_file.close()

		# for thunderbird
		if os.path.isfile(env_file) and proc_name == 'thunderbird':
			m_file = open(env_file, 'r')
			m_lines = m_file.readlines()
			m_head = m_lines[0]
			m_head = m_head.strip().split('\t')

			# change config file for each sample
			smaple_count = 0
			smaple_total = len(m_lines[1:])
			for m_line in m_lines[1:]:
				print m_line
				smaple_count += 1
				m_body = m_line.strip().split('\t')
				cfg_cmd = ''
				# for each environment variable
				for i in range(len(m_head)):
					tmp_cmd = 'echo \"user_pref(\\\"' + m_head[i] + '\\\", ' +\
						m_body[i] + ');\" >> ' + \
						'/home/zhouyangjia/.thunderbird/imrsy08x.default/prefs.js'
					cfg_cmd += tmp_cmd
					if i != len(m_head) -1:
						cfg_cmd += ' && '
				# for each epoch
				for i in range(epoch):
					sys.stdout.write('Epoch %d\tSample[%d/%d]: %s\n' % (i, \
						smaple_count, smaple_total, m_line.strip()))
					sample_name = 'sample_' + str(smaple_count)
					case_info = [domain, project, proc_name, sample_name, \
						cfg_cmd, start_cmd, '', stop_cmd, isroot, i]
					run_case(case_info)
			m_file.close()

		# for smplayer
		if os.path.isfile(env_file) and proc_name == 'smplayer':
			m_file = open(env_file, 'r')
			m_lines = m_file.readlines()
			m_head = m_lines[0]
			m_head = m_head.strip().split('\t')

			# change config file for each sample
			smaple_count = 0
			smaple_total = len(m_lines[1:])
			for m_line in m_lines[1:]:
				smaple_count += 1
				m_body = m_line.strip().split('\t')
				copyfile('/home/zhouyangjia/.config/smplayer/smplayer.ini.save', 
					'/home/zhouyangjia/.config/smplayer/smplayer.ini')
				# for each environment variable
				cfg_file = open('/home/zhouyangjia/.config/smplayer/smplayer.ini')
				cfg_str = cfg_file.read()
				for i in range(len(m_head)):
					str1 = m_head[i]
					str2 = m_head[i][:m_head[i].find('=')] + '=' + m_body[i]
					cfg_str = cfg_str.replace(str1, str2)
				cfg_file.close()
				cfg_file = open('/home/zhouyangjia/.config/smplayer/smplayer.ini', "w")
				cfg_file.write(cfg_str)
				# for each epoch
				for i in range(epoch):
					sys.stdout.write('Epoch %d\tSample[%d/%d]: %s\n' % (i, \
						smaple_count, smaple_total, m_line.strip()))
					sample_name = 'sample_' + str(smaple_count)
					case_info = [domain, project, proc_name, sample_name, \
						'', start_cmd, '', stop_cmd, isroot, i]
					run_case(case_info)
			m_file.close()


# if in testing step
if __name__ == "__main__":

	# global variables for command line arguments
	global traces_dir
	global conf_file
	global sleep_time
	global mode
	global epoch

	# default command line arguments
	traces_dir = './traces'
	conf_file = './test.ini'
	mode = 'normal'
	epoch = 2
	sleep_time = 3

	# parse command line options
	opts, args = getopt.getopt(sys.argv[1:], 'c:s:t:m:e:h')
	for op, value in opts:
		if op == '-t':
			traces_dir = value
		if op == '-c':
			conf_file = value
		if op == '-s':
			sleep_time = int(value)
		if op == '-m':
			mode = value
		if op == '-e':
			epoch = int(value)
		if op == '-h':
			usage()
			sys.exit(0)

	# main entrance of testing stage
	do_testing()

