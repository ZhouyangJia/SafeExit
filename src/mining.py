import os
import sys
import getopt
from sqlite3 import connect
import cProfile
import pstats
from io import BytesIO as StringIO
from difflib import SequenceMatcher


# usage of this script
def usage():
	print '%s: mine normal behaviors from sub-traces'%sys.argv[0]
	print 'Usage:'
	print '\tpython %s [-d <database_dir>]'%sys.argv[0]
	print '\tpython %s [-h]'%sys.argv[0]
	print 'Options:'
	print '\t-d specify the path of database'
	print '\t-h print help messages'


# key functions (31 key functions)
key_func = ['rmdir', 'unlink', 'ftruncate', 'rename', 'open', 'openat', \
	'creat', 'fsync', 'fdatasync', 'write', 'writev', 'pwrite64', 'fcntl', \
	'sendmmsg', 'sendto', 'sendmsg', 'io_submit', 'execve', 'kill', \
	'bind', 'flock', 'futex', 'mkdir', 'quotactl', 'exit_group', 'clone', \
	'chown', 'fchown', 'link', 'msync', 'munlockall']
# functions with path arg
path_func = ['open', 'creat', 'rmdir', 'unlink', 'chown', \
	'link', 'rename', 'openat', 'mkdir']
# functions with fd arg
fd_func = ['write', 'pwrite64', 'writev', 'fdatasync',\
	'sendto', 'sendmsg', 'sendmmsg', 'fcntl', 'flock',\
	'fsync', 'ftruncate', 'bind', 'fchown']
# functions that we care about the 1st arg more
one_arg_func = ['bind', 'fcntl', 'write', 'writev', 'pwrite64', \
	'sendto', 'sendmsg', 'sendmmsg', 'io_submit', 'execve', 'futex']
# functions that we care about all args
all_arg_func = ['quotactl', 'clone', 'munlockall', 'msync']
# output functions
output_func = ['io_submit', 'write', 'writev', 'pwrite64', \
	'sendto', 'sendmsg', 'sendmmsg']
# input functions
input_func = ['io_getevents', 'read', 'readv', 'pread64', \
	'recvfrom', 'recvmsg', 'recvmmsg']


# decorator to profile
def profile(fnc):
	def inner(*args, **kwargs):
		pr = cProfile.Profile()
		pr.enable()
		retval = fnc(*args, **kwargs)
		pr.disable()
		s = StringIO()
		ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
		ps.print_stats()
		print s.getvalue()
		return retval
	return inner


# helper function to store trace data into database
def insert_exitbehaivor(row):
	stmt = "INSERT INTO exit_behavior (TraceID, Domain, Project, Testcase, \
		PID, ExecTime, CallName, CallArgs, CallRet, Level, PIPE, Arg1, Arg2, \
		Arg3,Comment, Support, Total) \
		VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create exit_behavior table
def create_exitbehaivor():
	conn.execute("DROP TABLE IF EXISTS exit_behavior")
	stmt = "CREATE TABLE exit_behavior (ID INTEGER PRIMARY KEY AUTOINCREMENT,\
		TraceID, Domain, Project, Testcase, PID, Support, Total, ExecTime, \
		CallName, CallArgs, CallRet, Level, PIPE, Arg1, Arg2, Arg3, Comment)"
	conn.execute(stmt)
	stmt = "CREATE INDEX IF NOT EXISTS exitbehavior_index ON exit_behavior(ID)"
	conn.execute(stmt)


# get similarity of two strings
def similar(a, b):
	return SequenceMatcher(None, a, b).ratio()


# get common path of two paths
def get_comm_path(path1, path2):

	#remove quote
	path1 = path1.strip()
	path2 = path2.strip()
	if len(path1) >= 2:
		if path1[0] == '\"' and path1[-1] == '\"':
			path1 = path1[1:-1]
	if len(path2) >= 2:
		if path2[0] == '\"' and path2[-1] == '\"':
			path2 = path2[1:-1]

	if ' (deleted)' in path1:
		path1 = path1[:path1.find(' (deleted)')]
	if ' (deleted)' in path2:
		path2 = path2[:path2.find(' (deleted)')]

	# failed if the numbers of dir level are not equial
	dir1 = path1.split('/')
	dir2 = path2.split('/')
	if len(dir1) != len(dir2) or len(dir1) < 2:
		return ''

	# get position of name difference
	diff_pos = -1
	for i in range(len(dir1)):
		if dir1[i] != dir2[i]:
			if diff_pos == -1:
				diff_pos = i
			else:
				return ''

	# get sub string
	string1 = dir1[diff_pos]
	string2 = dir2[diff_pos]

	if diff_pos == len(dir1) - 1:
		if '.' in string1 and '.' in string2:
			if string1[:string1.rfind('.')] == string2[:string2.rfind('.')]:
				# merge dir names and return
				dir1[diff_pos] = string1[:string1.rfind('.')]
				ret = ''
				for item in dir1:
					ret += item+'/'

				return ret[:-1]

	match = SequenceMatcher(None, string1, string2).\
		find_longest_match(0, len(string1), 0, len(string2))
	sub_string = string1[match.a: match.a + match.size]

	prefix1_len = string1.find(sub_string)
	prefix2_len = string2.find(sub_string)

	surfix1_len = len(string1) - string1.find(sub_string) - match.size
	surfix2_len = len(string2) - string2.find(sub_string) - match.size
	
	if prefix1_len != prefix2_len and surfix1_len != surfix2_len:
		return ''

	if surfix1_len != 0 and prefix1_len != 0:
		sub_string = '*' * len(sub_string)

	for i in range(prefix1_len):
		sub_string = '*'+sub_string
	for i in range(surfix2_len):
		sub_string = sub_string+'*'

	# merge dir names and return
	dir1[diff_pos] = sub_string
	ret = ''
	for item in dir1:
		ret += item+'/'

	return ret[:-1]


# get procship of given test case, say we have 4 procs [444, 333, 222, 111]
# where 111's parent is 000, 222's parent is 111, 444 and 333's parent is 222. 
# we get:
#	pids = [111, 222, 333, 444]
#	procships = [[000, 222], [111, 333, 444], [222], [222]]
# in procships, each proc has an inner array, of which the first element is its
# parent, while the others are children (in ascending order).
def get_procship(project, testcase, epoch, signal):

	pids = []
	ppid_dict = {}
	procships = []

	stmt = "SELECT PPID, PID from procship where Project == '%s' and \
		Testcase == '%s' and Epoch == '%s' and Signal = '%s'" \
		%(project, testcase, epoch, signal)
	cursor = conn.execute(stmt)
	for row in cursor:
		if not row[1].isdigit():
			continue
			
		if not row[0].isdigit():
			continue

		if int(row[1]) < int(row[0]):
			continue

		pids.append(int(row[1]))
		ppid_dict[int(row[1])] = int(row[0])

	pids.sort()

	for mpid in pids:
		ppid = ppid_dict[mpid]
		procships.append([str(ppid)])
		if ppid in pids:
			procships[pids.index(ppid)].append(str(mpid))
			
	for i in range(len(pids)):
		pids[i] = str(pids[i])

	return pids, procships


# get pid-tid relationship in given test case
def get_piddict(project, testcase, epoch, signal):
	get_pid = {}
	stmt = "SELECT PID, TID from threads where Project == '%s' and \
		Testcase == '%s' and Epoch == '%s' and Signal = '%s'" \
		%(project, testcase, epoch, signal)
	cursor = conn.execute(stmt)
	for row in cursor:
		mpid = str(row[0])
		mtid = str(row[1])
		get_pid[mtid] = mpid
	return get_pid


# get port number and s_port_type (the 1st arg of input/output func).
# for 5<UNIX:[111]>, port=111, port_type=UNIX
def get_port(arg):
	# for 5<UNIX:[111]>
	if arg[-1] == '>':
		arg = arg[:-1]
	port = arg.split('<')[-1] # get UNIX:[111]
	port_type = ''
	# path fd
	if not ':' in port:
		return '','','',''

	port_type = port[:port.find(':')] # get UNIX
	port = port[port.find(':')+1:] # get 111
	if port[0] == '[':
		port = port[1:]
	if port[-1] == ']':
		port = port[:-1]

	# parse connected sockets
	port_from = ''
	port_to = ''
	if '->' in port:
		port_tmp = port.split('->')
		port_from = port_tmp[0] # get 313849
		port_to = port_tmp[1] # get 313850
	return port, port_type, port_from, port_to



# get pipe path by using breadth-first-search with search-path recorded
def get_path(s_pid_num, t_pid_num, pid_list, procship_list):

	pipe = []
	search_list = [s_pid_num]
	father_dict = {}
	father_dict[s_pid_num] = s_pid_num
	has_visited = {}
	while len(search_list):
		search_head = search_list[0]
		search_list = search_list[1:]
		has_visited[search_head] = True

		# if find the target pid
		if search_head == t_pid_num:
			search_path = []
			while father_dict[search_head] != search_head:
				my_father = father_dict[search_head]
				father_index = pid_list.index(my_father)
				my_pipe = procship_list[father_index].index(search_head)
				search_path.append(my_pipe)
				search_head = my_father
			for node in reversed(search_path):
				pipe.append(node)
			return pipe

		# search son nodes
		search_index = pid_list.index(search_head)
		search_array = procship_list[search_index]
		for i in range(len(search_array)):
			if has_visited.has_key(search_array[i]):
				continue
			if not search_array[i] in pid_list:
				continue
			search_list.append(search_array[i])
			father_dict[search_array[i]] = search_head
	return []


# get the pipe line from source pid to target pid according to procship.
# given pids and procships:
#	pids = [111, 222, 333, 444]
#	procships = [[000, 222], [111, 333, 444], [222], [222]]
# if write from 111 and read from 444, the pipe should be []:[1,2]
#	(0th pids)'s (1st child)'s (2nd child)
# if write from 444 and read from 111, the pipe should be [1, 2]:[0, 0]
#	(3rd pids)'s (parent)'s (parent), while the 3rd pids is [1, 2].
# if write from 333 and read from 444, the pipe should be [1, 1]:[0, 2]
#	(2nd pids)'s (parent)'s (2nd child), while the 2nd pids is [1, 1].
def get_pidpipe(syscall, pid_list, procship_list, get_pid_dict):

	# dereference infomation in row
	[trace_id, domain, project, testcase, epoch, signal, \
		# source call info (s_call_name) VS. target call info (t_call_name)
		s_pid_num, s_exec_time, s_call_name, s_call_args, s_call_ret] = syscall

	# if s_pid_num is unknown, return
	if not get_pid_dict.has_key(s_pid_num):
		return -1
	s_pid_num = get_pid_dict[s_pid_num]
	if not s_pid_num in pid_list:
		return -1

	main_pid = pid_list[0]
	pid_path = get_path(main_pid, s_pid_num, pid_list, procship_list)
	pipe = str(pid_path)

	# get t_pid_num
	t_pid_num = ''
	t_info = ''
	if s_call_name == 'kill':
		t_pid_num = s_call_args.split(',')[0]
	elif s_call_name == 'clone':
		t_pid_num = s_call_ret
	elif s_call_name not in output_func:
		return pipe
	else:

		# get s_port number and s_port_type (the 1st arg of input/output func).
		s_port = ''
		s_port_type = ''
		s_port_from = ''
		s_port_to = ''
		if s_call_name == output_func[0]:
			# for io_submit
			s_port = s_call_args.split(',')[0]
		else:
			s_port, s_port_type, s_port_from, s_port_to = get_port( \
					s_call_args.split(',')[0])
			# path fd
			if s_port == '' and s_port_type == '':
				return pipe
		

		# try to find the targets in openfd
		# for UNIX fd
		if s_port_type == 'UNIX':
			if s_port_from == '' or s_port_to == '':
				return -1

			# find target 
			cur_process = False
			stmt = "SELECT DISTINCT CMD, PID, NAME FROM openfd WHERE \
				NODE == '%s' AND Project == '%s' AND Testcase == '%s' AND \
				Epoch == '%s'"%(s_port_to, project, testcase, epoch)
			cursor = conn.execute(stmt)
			for row in cursor:
				if row[1] == s_pid_num:
					cur_process = True
					continue
				t_pid_num = row[1]
				t_info = row[0] + '(' + row[2] + ')'
				break

			if t_pid_num == '' and cur_process:
				t_pid_num = 'cur_process'

		elif s_port_type == 'pipe':

			# find target 
			cur_process = False
			stmt = "SELECT DISTINCT CMD, PID, MODE, NAME FROM openfd WHERE \
				NODE == '%s' AND Project == '%s' AND Testcase == '%s' AND \
				Epoch == '%s'"%(s_port, project, testcase, epoch)
			cursor = conn.execute(stmt)
			for row in cursor:
				if row[1] == s_pid_num:
					cur_process = True
					continue
				if 'r' not in row[2]:
					continue
				t_pid_num = row[1]
				t_info = row[0] + '(' + row[3] + ')'
				break

			if t_pid_num == '' and cur_process:
				t_pid_num = 'cur_process'

		elif s_port_type == 'UDP' or s_port_type == 'TCP':
			t_pid_num = 'fix_target'
			t_info = s_port

		elif s_port_type == 'NETLINK':
			t_pid_num = 'fix_target'
			t_info = 'kernel'

		elif s_port_type == 'anon_inode':
			t_pid_num = 'ignore'


		# try to find read methods in other processes of current program
		if t_pid_num == '':
			# get the name of corresponding read method
			index = output_func.index(s_call_name)
			t_call_name = input_func[index]

			# get target candidates
			stmt = "SELECT PID, CallArgs, CallRet FROM exit_traces WHERE \
				Project == '%s' AND Testcase == '%s' AND \
				Epoch == '%s' AND Signal == '%s' AND \
				ExecTime > '%s' AND \
				(CallName == 'read' OR CallName == 'pread64' OR \
				CallName == 'readv' OR CallName == 'sendmmsg' OR \
				CallName == 'sendmsg' OR CallName == 'sendto' OR \
				CallName == 'io_getevents')"  \
				%(project, testcase, epoch, signal, s_exec_time)
			cursor = conn.execute(stmt)
			# check target candidates
			for row in cursor:
				t_call_args = str(row[1])
				t_call_ret = str(row[2])

				# skip failed calls
				if '-1 ' in t_call_ret:
					continue

				# get t_port number and t_port_type
				t_port = ''
				t_port_type = ''
				t_port_from = ''
				t_port_to = ''
				if t_call_name == input_func[0]:
					# for io_getevents
					t_port = t_call_args.split(',')[0]
				else:
					t_port, t_port_type, t_port_from, t_port_to = get_port( \
						t_call_args.split(',')[0])

				if s_port == t_port and s_port_type == t_port_type:
					t_pid_num = str(row[0])
					break
				if s_port_from.isdigit() and s_port_to.isdigit() and \
					t_port_from.isdigit() and t_port_to.isdigit():
					if s_port_type == t_port_type and \
						int(s_port_from) + int(s_port_to) == \
						int(t_port_from) + int(t_port_to):
						t_pid_num = str(row[0])
						break

		# try to find new fd assciated with resource beyond current program
		if t_pid_num == '':
			# get connect syscalls in exit phase
			stmt = "SELECT CallArgs, CallRet FROM exit_traces WHERE \
				Project == '%s' AND Testcase == '%s' AND \
				Epoch == '%s' AND Signal == '%s' AND \
				CallName == 'connect'"%(project, testcase, epoch, signal)
			cursor = conn.execute(stmt)

			# check each connect syscall
			# 3<UNIX:[341873]>, {sa_family=AF_LOCAL, sun_path=@"/tmp..."}, 20
			for row in cursor:
				myarg = row[0]
				myret = row[1]
				# skip failed calls
				if '-1 ' in myret:
					continue
				# only focus on unix fd
				if 'UNIX' not in myarg:
					continue

				# get port_from
				myport = myarg.split(',')[0] # get 3<UNIX:[341873]>
				myport = myport[:-1].split('<')[-1] # get UNIX:[341873]
				myport = myport.split(':')[-1][1:-1] # get 341873

				# get target file
				myfile = myarg[myarg.find('sun_path=')+9:myarg.find('}')]
				if s_port_from == myport:
					t_pid_num = 'fix_target'
					t_info = myfile
					break

	if t_pid_num == '':
		# still not found, report
		return -1 #error return
	if t_pid_num == 'cur_process':
		return 0 #normal return
	if t_pid_num == 'ignore':
		return 0
	if t_pid_num == 'fix_target':
		return pipe + ':' + str([t_info])
	
	# we can not recognize the pid
	if not get_pid_dict.has_key(t_pid_num):
		# maybe belongs to other program
		if t_info != '':
			return pipe + ':' + str([t_info])
		else:
			return -1

	# we can recognize the pid
	t_pid_num = get_pid_dict[t_pid_num]
	if not t_pid_num in pid_list:
		# this should never happen
		return -1

	# kill/clone to the process itself
	if s_pid_num == t_pid_num:
		# kill itself
		if s_call_name == 'kill':
			return pipe
		# clone threads
		else:
			return 0

	pid_path = get_path(s_pid_num, t_pid_num, pid_list, procship_list)
	if len(pid_path):
		return pipe + ':' + str(pid_path)
	else:
		# this should never happen
		print 'Unexcepted behaivors in get_pidpipe'
		return -1


# sort call_list according to the similarity of n_arg0 and m_args0
def sort_call_list(call_list, call_name, m_args0):

	for i in range(len(call_list)):
		for j in range(i + 1, len(call_list)):

			n_args0_i = ''
			n_args0_j = ''

			[n_pid_num, n_exec_time, n_call_args, n_call_ret] = call_list[i]
			n_args = n_call_args.split(',') + ['', '', '']
			n_args0_i = n_args[0]
			if call_name in fd_func:
				n_args0_i = n_args[0][:-1].split('<')[-1]

			[n_pid_num, n_exec_time, n_call_args, n_call_ret] = call_list[j]
			n_args = n_call_args.split(',') + ['', '', '']
			n_args0_j = n_args[0]
			if call_name in fd_func:
				n_args0_j = n_args[0][:-1].split('<')[-1]

			if similar(n_args0_i, m_args0) < similar(n_args0_j, m_args0):
				call_tmp = call_list[i]
				call_list[i] = call_list[j]
				call_list[j] = call_tmp

	return call_list


# confirm exit behaivors cross different epoches
def confirm_behavior(project, testcase, epoch_list, signal, call_name, \
	call_args, pid_pipe):

	# to distinguish different args and pipes
	m_call_args = call_args
	m_pid_pipe = pid_pipe
	m_call_pid = m_pid_pipe.split(':')[0]
	m_args = m_call_args.split(',') + ['', '', '']
	# filter out the effect of fd, e.g., 3</path/to/file>
	if call_name in fd_func:
		m_args[0] = m_args[0][:-1].split('<')[-1]

	# complete_match or partial match
	complete_match = []

	# for partial match oens, we add extra comment
	comment = ''

	# count for support epoch
	cnt = 0
	# iterate test epoch
	for epoch in epoch_list:
		cnt += 1
		#print 'case111 '+case+' m_args '+str(m_args)
		
		# get procship of current epoch
		n_pid_list, n_procship_list = get_procship(project, testcase, \
			epoch, signal)

		# get_pid_dict: get pid of given tid
		n_get_pid_dict = get_piddict(project, testcase, epoch, signal)

		# get calls with the same names
		stmt = "SELECT PID, ExecTime, CallArgs, CallRet FROM exit_traces \
			WHERE Project == '%s' and TestCase == '%s' and Epoch == '%s' and \
			Signal == '%s' and CallName == '%s'" \
			%(project, testcase, epoch, signal, call_name)
		cursor = conn.execute(stmt)

		# collect calls in this epoch
		call_list = []
		argkey_dict = {}
		for row in cursor:

			# ignore the failed calls
			pid_num = str(row[0])
			call_args = str(row[2])
			call_ret = str(row[3])
			if '-1 ' in call_ret:
				continue

			# continue if call pids are not equal
			if not n_get_pid_dict.has_key(pid_num):
				continue
			tgid_num = n_get_pid_dict[pid_num]
			if tgid_num not in n_pid_list:
				continue

			n_main_pid = n_pid_list[0]
			n_pid_path = get_path(n_main_pid, tgid_num, \
				n_pid_list, n_procship_list)
			n_call_pid = str(n_pid_path)
			if n_call_pid != m_call_pid:
				continue

			# if a call appears multiple times, only confirm the first time
			tgid_num = ''
			if n_get_pid_dict.has_key(pid_num):
				tgid_num = n_get_pid_dict[pid_num]
			args = call_args.split(',')
			argkey =  tgid_num + call_name + call_args
			if call_name in output_func:
				argkey =  tgid_num + call_name + args[0]
			if not argkey_dict.has_key(argkey):
				argkey_dict[argkey] = 1
			else:
				continue

			call_list.append([str(row[0]), str(row[1]), \
					str(row[2]), str(row[3])])

		# get n_pid_pipe for each call and store into n_pid_pipe_dict
		n_pid_pipe_dict = {}
		for n_pid_num, n_exec_time, n_call_args, n_call_ret in call_list:
			
			n_syscall = ['', 'domain', project, testcase, epoch, signal, \
				n_pid_num, n_exec_time, call_name, n_call_args, n_call_ret]
			n_pid_pipe = get_pidpipe(n_syscall, n_pid_list, \
				n_procship_list, n_get_pid_dict)
			n_pid_pipe_dict[n_pid_num+n_exec_time+n_call_args] = n_pid_pipe

		# search for matched behavior, first try: complete match
		isconfirmed = False
		for n_pid_num, n_exec_time, n_call_args, n_call_ret in call_list:

			# if m_pid_pipe doesn't equal to n_pid_pipe, skip
			n_pid_pipe = n_pid_pipe_dict[n_pid_num+n_exec_time+n_call_args]
			if str(m_pid_pipe) != str(n_pid_pipe):
				continue
			n_args = n_call_args.split(',') + ['', '', '']

			# complete match for fd_func
			if call_name in fd_func:

				# filter out the effect of fd, e.g., 3</path/to/file>
				n_args[0] = n_args[0][:-1].split('<')[-1]

				# for output_func
				if call_name in output_func:
					# path fd
					if ':' not in m_args[0] and ':' not in n_args[0]:
						if m_args[0] == n_args[0]:
							isconfirmed = True
							break
					# sock/unix-like fd
					if ':' in m_args[0] and ':' in n_args[0]:
						if len(n_pid_pipe) > 1:
							isconfirmed = True
							break
				else:
					if call_name == 'ftruncate':
						if m_args[0] == n_args[0]:
							isconfirmed = True
							break

					if m_args == n_args:
						isconfirmed = True
						break

			# complete match for kill
			if call_name == 'kill':
				if m_args[1:] == n_args[1:] and n_pid_pipe[0] != -1:
					isconfirmed = True
					break

			# complete match for clone
			if call_name == 'clone':
				if n_pid_pipe[0] != -1:
					isconfirmed = True
					break

			# complete match for path_func
			if m_args == n_args:
				isconfirmed = True
				break
			
		# matched in level 1
		if isconfirmed:
			complete_match.append(True)
			continue

		# search for matched behavior, second try: partial match
		call_list = sort_call_list(call_list, call_name, m_args[0])
		for n_pid_num, n_exec_time, n_call_args, n_call_ret in call_list:

			# if m_pid_pipe doesn't equal to n_pid_pipe, skip
			n_pid_pipe = n_pid_pipe_dict[n_pid_num+n_exec_time+n_call_args]
			if str(m_pid_pipe) != str(n_pid_pipe):
				continue

			n_args = n_call_args.split(',') + ['', '', '']

			# partial match for path_func, use dir instead of path
			if call_name in path_func:
				# get common path of two paths
				common_path = get_comm_path(m_args[0], n_args[0])
				if call_name == 'openat':
					common_path = get_comm_path(m_args[1], n_args[1])
				if common_path != '':
					if call_name == 'openat':
						m_args[1] = n_args[1] = common_path
					else:
						m_args[0] = n_args[0] = common_path

					# for rename, there are two dir
					if call_name == 'rename':
						common_path2 = get_comm_path(m_args[1], n_args[1])
						if common_path2 != '':
							m_args[1] = n_args[1] = common_path2

				if common_path != '' and m_args == n_args:
					comment = m_args[0]
					if call_name == 'rename':
						comment += ':'+m_args[1]
					if call_name == 'openat':
						comment += m_args[1]
					isconfirmed = True
					break

			# partial match for fd_func
			if call_name in fd_func:
				# filter out the effect of fd, e.g., 3</path/to/file>
				n_args[0] = n_args[0][:-1].split('<')[-1]
				# for path fd
				if ':' not in m_args[0] and ':' not in n_args[0]:
					# get common path of two paths
					common_path = get_comm_path(m_args[0], n_args[0])
					if common_path != '':
						m_args[0] = n_args[0] = common_path
					# for output_func, only compare the content in fd
					if call_name in output_func:
						if common_path != '':
							comment = m_args[0]
							isconfirmed = True
							break
					else:
						if common_path != '' and call_name == 'ftruncate':
							if m_args[0] == n_args[0]:
								comment = m_args[0]
								isconfirmed = True
								break
						if common_path != '' and m_args == n_args:
							comment = m_args[0]
							isconfirmed = True
							break

				# sock/unix-like fd
				if ':' in m_args[0] and ':' in n_args[0]:
					if call_name in output_func:
						if len(n_pid_pipe) > 1:
							isconfirmed = True
							break

			# partial match for exit_group
			if call_name == 'exit_group':
				if n_pid_pipe[0] != -1:
					isconfirmed = True
					break

		# matched in level 2
		if isconfirmed:
			complete_match.append(False)
			continue

		# no matched behavior in any test case would deny the behavior
		if not isconfirmed:
			cnt -= 1
			continue

	# collect args properly
	ret_args = []
	if call_name in one_arg_func:
		first_arg = m_call_args.split(',')[0]
		second_arg = m_call_args[len(first_arg) + 1:]
		ret_args.append(first_arg)
		ret_args.append(second_arg)
	elif call_name in all_arg_func:
		ret_args.append(m_call_args)
	else:
		ret_args = m_call_args.split(',')
	ret_args += ['', '', '']

	# remove "" or fd<> for ret_args
	for i in range(len(ret_args)):
		ret_args[i] = ret_args[i].strip()
		if len(ret_args[i]) >= 2:
			if ret_args[i][0] == '\"' and ret_args[i][-1] == '\"':
				ret_args[i] = ret_args[i][1:-1]
			if ret_args[i][-1] == '>':
				ret_args[i] = ret_args[i][:-1]
				ret_args[i] = ret_args[i][ret_args[i].find('<')+1:]

	# complete match in all test cases
	if all(complete_match):
		return ['complete'] + [str(m_pid_pipe)] + ret_args[:3] + [comment], cnt
	# partial match in any test case
	else:
		return ['partial'] + [str(m_pid_pipe)] + ret_args[:3] + [comment], cnt


# analyze calls of important syscalls in exit phase
def analyze_syscalls(myrow):

	if len(myrow) == 0:
		return

	myproject = myrow[0][2]
	mycase = myrow[0][3]
	myepoch = myrow[0][4]
	print 'mining:',myproject,mycase,myepoch

	# get epoch lists used to confirm behavior
	epoch_list = []
	stmt = "SELECT DISTINCT Epoch FROM exit_traces \
		WHERE Project=='%s' AND Testcase=='%s'"%(myproject, mycase)
	cursor = conn.execute(stmt)
	for row in cursor:
		if 'signal' in str(row[0]):
			continue
		epoch_list.append(str(row[0]))
	epoch_list.remove(myepoch)

	# get procship of current epoch
	pid_list, procship_list = get_procship(myproject, mycase, myepoch, '0')

	# build get_pid_dict for current epoch
	# get_pid_dict: get pid of given tid
	get_pid_dict = get_piddict(myproject, mycase, myepoch, '0')

	cnt = 0
	for syscall in myrow:
		cnt += 1

		# dereference infomation in row
		[trace_id, domain, project, testcase, epoch, signal, pid_num, \
			exec_time, call_name, call_args, call_ret] = syscall

		# confirm call behavior on other epochs
		pid_pipe = get_pidpipe(syscall, pid_list, procship_list, get_pid_dict)
		if pid_pipe == 0:
			continue
		if pid_pipe == -1:
			#print 'Unknown output targets:'
			#print syscall
			continue

		res,support = confirm_behavior(myproject, mycase, epoch_list, '0', \
			call_name, call_args, pid_pipe)
		if len(res) == 0:
			continue
		res = [trace_id, domain, project, testcase, pid_num, \
			exec_time, call_name, call_args, call_ret] + res
		res += [str(support),str(len(epoch_list))]
		insert_exitbehaivor(res)


def do_mining():

	# create exit_behavior table
	create_exitbehaivor()

	# select projects and test cases
	cursor = conn.execute("SELECT DISTINCT Project, Testcase, Epoch \
		from exit_traces")
	proj_case_dict = {}
	for row in cursor:
		project = row[0]
		testcase = row[1]
		epoch = row[2]
		if 'signal' in epoch:
			continue
		# choose one baseline epoch for each testcase
		if not proj_case_dict.has_key(project + testcase):
			proj_case_dict[project + testcase] = True
		else:
			continue

		# select the call sites from exit phase of normal-exit trace
		stmt = """
			SELECT * FROM exit_traces
			WHERE Project == '%s' AND Testcase == '%s' AND 
				Epoch == '%s' AND Signal == '0'
			ORDER BY
				ExecTime ASC
			""" % (project, testcase, epoch)
		cursor1 = conn.execute(stmt)
		myrow = []
		for row1 in cursor1:
			if row1[-3] in key_func:
				myrow.append(row1)
		analyze_syscalls(myrow)


# if in mining step
if __name__ == "__main__":

	global conn

	# parse command line options
	database_dir = './traces.db'
	opts, args = getopt.getopt(sys.argv[1:], 'd:h')
	for op, value in opts:
		if op == '-d':
			database_dir = value
		if op == '-h':
			usage()
			sys.exit(0)

	conn = connect(database_dir)
	conn.text_factory = str
	do_mining()
	conn.commit()
	conn.close()
