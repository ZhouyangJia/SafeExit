import os
import sys
import getopt
import mining
from sqlite3 import connect
#import numpy as np
#import matplotlib.pyplot as plt


# usage of this script
def usage():
	print '%s: cluster exit normal behaviors'%sys.argv[0]
	print 'Usage:'
	print '\tpython %s [-d <database_dir>]'%sys.argv[0]
	print '\tpython %s [-h]'%sys.argv[0]
	print 'Options:'
	print '\t-d specify the path of database'
	print '\t-h print help messages'


# helper function to store clusters into database
def insert_cluster(row):
	stmt = "INSERT INTO exit_cluster (Domain, Project, Testcase, PID, \
		BehaviorID, Pipe, AllSupport, PatternID, Pattern, X, Y, Z) \
		VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create cluster table
def create_cluster():
	conn.execute("DROP TABLE IF EXISTS exit_cluster")
	stmt = "CREATE TABLE exit_cluster (ID INTEGER PRIMARY KEY AUTOINCREMENT,\
		Domain, Project, Testcase, PID, BehaviorID, Pipe, AllSupport, \
		PatternID, Pattern, X, Y, Z)"
	conn.execute(stmt)
	stmt = "CREATE INDEX IF NOT EXISTS exitcluster_index ON exit_cluster(ID)"
	conn.execute(stmt)


# statistcs: Behavior-number Distribution of Clusters
def draw_cluster_number(lenghts):
	length_dict = {}
	for length in lenghts:
		length = length.strip()
		length = length.split()[-2]

		if not length.isdigit():
			continue
		length = int(length)
		if length_dict.has_key(length):
			length_dict[length] += 1
		else:
			length_dict[length] = 1

	res = sorted((key, value) for (key,value) in length_dict.items())
	lengths = [key for (key,value) in res]
	counts = [value for (key,value) in res]
	y_pos = np.arange(len(lengths))

	bc = plt.bar(y_pos[1:], counts[1:], align='center', alpha=0.5)
	plt.xticks(y_pos[1:], lengths[1:])
	plt.ylabel('Behavior frequency')
	plt.ylim(0, 200)
	plt.xlabel('Behavior number')

	rects = bc.patches
	labels = ["%d" % i for i in counts[1:]]
	for rect, label in zip(rects, labels):
		height = rect.get_height()
		plt.annotate(label, (rect.get_x() + rect.get_width() / 2, height + 5),
			ha='center', va='bottom')

	plt.title('Behavior-number Distribution of Clusters')
	plt.show()


# statistcs: Behavior-number Distribution of Cluster Patterns
def draw_pattern_behavior(pattern_unloop):
	plenghts = []
	for pattern in pattern_unloop:
		plenghts.append(pattern)

	length_dict = {}
	for length in plenghts:
		length = length.strip()
		length = length[:2]

		if not length.isdigit():
			continue
		length = int(length)
		if length_dict.has_key(length):
			length_dict[length] += 1
		else:
			length_dict[length] = 1

	res = sorted((key, value) for (key,value) in length_dict.items())
	lengths = [key for (key,value) in res]
	counts = [value for (key,value) in res]
	y_pos = np.arange(len(lengths))

	bc = plt.bar(y_pos, counts, align='center', alpha=0.5)
	plt.xticks(y_pos, lengths)
	plt.ylabel('Behavior frequency')
	plt.ylim(0, 18)
	plt.xlabel('Behavior number')

	rects = bc.patches
	labels = ["%d" % i for i in counts]
	for rect, label in zip(rects, labels):
		height = rect.get_height()
		plt.annotate(label, (rect.get_x() + rect.get_width() / 2, height + 1),
			ha='center', va='bottom')

	plt.title('Behavior-number Distribution of Cluster Patterns')
	plt.show()


# statistcs: Cluster-number Distribution of Cluster Patterns
def draw_pattern_number(pattern_unloop, patterns, pattern_dict):
	# the first num patterns are single-behavior patterns, skip 
	num = 0
	for pattern in pattern_unloop:
		if pattern.find('01') == 0:
			num += 1

	cluster_ids = [x for x in range(1, len(pattern_unloop) + 1 - num)]
	count_ids = [0 for x in range(len(pattern_unloop))]
	y_pos = np.arange(len(cluster_ids))
	for pattern in patterns:

		length = 0
		for c in pattern:
			if c == '(':
				length += 1
		if length <= 1:
			continue

		unlooped = pattern_dict[pattern]
		if unlooped not in pattern_unloop:
			continue
		index = pattern_unloop.index(unlooped)
		count_ids[index] += 1

	bc = plt.bar(y_pos, count_ids[num:], align='center', alpha=0.5)
	plt.xticks(y_pos, cluster_ids)
	plt.ylabel('Cluster frequency')
	plt.ylim(0, 120)
	plt.xlabel('Cluster pattern ID')

	rects = bc.patches
	labels = ["%d" % i for i in count_ids[num:]]
	for rect, label in zip(rects, labels):
		height = rect.get_height()
		plt.annotate(label, (rect.get_x() + rect.get_width() / 2, height + 1),
			ha='center', va='bottom')

	plt.title('Cluster-number Distribution of Cluster Patterns')
	plt.show()


# get similarity of two strings
def similar(a, b):
	return SequenceMatcher(None, a, b).ratio()


# return cluster of a given syscall_list
# cluster_list stores clusters like:
#	['nginx_case_1_0', '0', '7289', 'unlink', '/run/nginx.pid']
#	Pattern:	(unlink x)
#	Behavior_id: [1, 2, 3]
#	Pipe: [pipe]
#	Info: nginx_case_1_0 0 7289 1 1
#	Resource x: /run/nginx.pid
#
def get_cluster(info, syscall_list):

	if len(syscall_list) == 0:
		return []

	cluster_list = []

	if len(syscall_list) == 0:
		return []

	symbol = ['x', 'y', 'z', 'o']
	count = 0

	resource_dict = {}
	result_str = ''
	pid_str = ''
	pipe_str = ''
	id_str = ''
	is_support = True
	last_syscall = []
	for syscall in syscall_list:
		if syscall == last_syscall:
			continue
		else:
			last_syscall = syscall
			call_name = syscall[6]
			if call_name == 'open':
				call_name = 'creat'
			if call_name == 'openat':
				call_name = 'creat'
			if call_name == 'pwrite64':
				call_name = 'write'
			if call_name == 'fdatasync':
				call_name = 'fsync'
			result_str += '\t('+call_name
			id_str += ' '+str(syscall[2])
			pid_str = ' '+syscall[1]
			pipe_str = ' '+syscall[3]
			if syscall[4] != syscall[5]:
				is_support = False

			for resource in syscall[7:]:
				# for partial resource, use their partial form
				if '(' in resource and ')' in resource:
					resource = resource[resource.find('(') + 1:-1]
				if resource_dict.has_key(resource):
					result_str += ' '+symbol[resource_dict[resource]]
				else:
					sub_path = False
					for key,value in resource_dict.items():
						if resource.endswith(key) or key.endswith(resource):
							result_str += ' '+symbol[value]
							if len(resource) > len(key):
								resource_dict.pop(key)
								resource_dict[resource] = value
							sub_path = True
							break

					if not sub_path:
						resource_dict[resource] = count
						result_str += ' '+symbol[count]
						if count < 3:
							count += 1

			result_str += ')'
			cluster_list.append(str(info + syscall))

	res = sorted((key, value) for (key,value) in resource_dict.items())

	if len(res) >= 2:
		key1,value1 = res[0]
		key2,value2 = res[1]

		if key1 in key2:
			result_str += '\t[%s in %s]'%(symbol[value1], symbol[value2])
		if key2 in key1:
			result_str += '\t[%s in %s]'%(symbol[value2], symbol[value1])

		if len(res) == 3:
			key3,value3 = res[2]

			if key1 in key3:
				result_str += '\t[%s in %s]'%(symbol[value1], symbol[value3])
			if key3 in key1:
				result_str += '\t[%s in %s]'%(symbol[value3], symbol[value1])

			if key3 in key2:
				result_str += '\t[%s in %s]'%(symbol[value3], symbol[value2])
			if key2 in key3:
				result_str += '\t[%s in %s]'%(symbol[value2], symbol[value3])

	cluster_list.append('Pattern:'+result_str)
	cluster_list.append('PID:'+pid_str)
	cluster_list.append('Behavior_id:'+id_str)
	cluster_list.append('Pipe:'+pipe_str)
	cluster_list.append('Support: '+str(is_support))
	length = 0
	for c in result_str:
		if c == '(':
			length += 1

	info_str = ''
	info_str += 'Info: '
	for item in info:
		info_str += item + ' '
	info_str += str(length) + ' '
	info_str += str(len(res))
	cluster_list.append(info_str)
	for item in res:
		cluster_list.append('Resource '+symbol[item[1]]+': '+item[0])
	cluster_list.append('')

	return cluster_list


# get resource of given syscall
def get_resource(syscall_info):

	resource = []

	# dereference infomation in row
	[pid_num, call_name, call_args, call_ret] = syscall_info
	args = call_args.split(',')

	if call_name == 'rename':
		rename_from = args[0][1:-1]
		rename_to = args[1][2:-1]
		resource = [rename_from, rename_to]
	elif call_name == 'kill':
		resource = [args[0]]
	elif call_name == 'execve':
		resource = [args[0]]
	elif call_name == 'clone':
		resource = [call_ret]
	elif call_name == 'futex':
		resource = [args[0]]
	elif call_name == 'openat':
		resource = [args[1][1:-1]]
	elif call_name == 'exit_group':
		resource = [args[0]]
	elif call_name == 'io_submit':
		resource = [args[0]]
	elif call_name == 'msync':
		resource = [args[0]]
	elif call_name == 'munlockall':
		resource = ['VOID']
	elif call_name in mining.fd_func:
		if args[0][-1] == '>':
			resource = [args[0][:-1].split('<')[-1]]
		else:
			resource = [args[0].split('<')[-1]+']']
	elif call_name in mining.path_func:
		resource = [args[0][1:-1]]

	for i in range(len(resource)):
		if resource[i].find('/run') == 0:
			resource[i] = '/var' + resource[i]

		if ' (deleted)' in resource[i]:
			resource[i] = resource[i][:resource[i].find(' (deleted)')]

	return tuple(resource)


# check whether two paths (resources) are equal
def is_equal(path1, path2):
	#print 'compare: '+path1+'***'+path2
	if path1 == '' or path2 == '':
		return False

	if '/' not in path1 or '/' not in path2:
		return path1 == path2

	path1 = path1.replace('./','/')
	path2 = path2.replace('./','/')
	if path1 in path2 or path2 in path1:
		return True

	return False


# remove loop for a given cluster
def remove_loop(pattern):

	operations = pattern.split('\t')[1:]
	loop_number = len(operations) / 2 + 1
	# length of loop
	for i in range(1, loop_number):
		# keep find loop in op with lengh of i
		not_fixed = True
		while(not_fixed):
			not_fixed = False
			op_number = len(operations)
			for j in range(op_number):
				if j - i < 0 or j + i > op_number:
					continue
				if operations[j-i:j] == operations[j:j+i]:
					operations = operations[:j] + operations[j+i:]
					not_fixed = True
					break
	
	# add behavior number in pattern_str
	pattern_str = ''
	length = len(operations)
	for op in operations:
		pattern_str += ' '+op
		if '[' in op:
			length -= 1
	if length < 10:
		pattern_str = '0'+str(length) + pattern_str
	else:
		pattern_str = str(length) + pattern_str

	return pattern_str


# abstrace the clusters to cluster patterns
def get_pattern(cluster_list):

	create_cluster()

	patterns = []
	lenghts = []
	for line in cluster_list:
		line = line.strip()
		if 'Pattern' in line:
			patterns.append(line)
		if 'Info' in line:
			lenghts.append(line)

	# remove loops in clusters
	pattern_dict = {}
	pattern_unloop = []
	for pattern in patterns:
		pattern_str = remove_loop(pattern)
		pattern_unloop.append(pattern_str)
		pattern_dict[pattern] = pattern_str

	# remove duplicate and sort
	pattern_unloop = list(set(pattern_unloop))
	pattern_unloop.sort()
	#for pattern in pattern_unloop:
	#	print pattern

	#draw_cluster_number(lenghts)
	#draw_pattern_behavior(pattern_unloop)
	#draw_pattern_number(pattern_unloop, patterns, pattern_dict)

	return pattern_unloop


def get_cluster_list(mode):

	# return value
	cluster_list = []

	# for each pid
	stmt = ""
	if mode == 'trace':
		stmt = "SELECT DISTINCT Domain, Project, Testcase, Epoch, Signal, PID \
				FROM exit_traces ORDER BY PID ASC"
	elif mode == 'behavior':
		stmt = "SELECT DISTINCT Domain, Project, Testcase, PID \
				FROM exit_behavior ORDER BY PID ASC"
	else:
		return []

	cursor = conn.execute(stmt)
	for row in cursor:

		# collect syscall lists
		stmt = ""
		if mode == 'trace':
			[domain, project, test_case, epoch, signal, pid_num] = row
			info = [domain, project, test_case, epoch, signal, pid_num]

			# select the call sites from exit phase
			stmt = """
				SELECT ID, Domain, Project, Testcase, Epoch, Signal, PID, 
					ExecTime, CallName, CallArgs, CallRet FROM exit_traces
				WHERE Project == '%s' AND Testcase == '%s' AND Epoch == '%s' 
				AND Signal == '%s' AND PID = '%s' ORDER BY ExecTime ASC
				""" % (project, test_case, epoch, signal, pid_num)

		elif mode == 'behavior':
			[domain, project, test_case, pid_num] = row

			info = [domain, project, test_case, pid_num]

			# select the call sites from exit phase
			stmt = """
				SELECT ID, Domain, Project, Testcase, PID, Support, Total, ExecTime, 
					CallName, CallArgs, CallRet, Level, PIPE, Comment 
				FROM exit_behavior
				WHERE Project == '%s' AND Testcase = '%s' AND PID == '%s'
				ORDER BY ExecTime ASC
				""" % (project, test_case, pid_num)

		cursor1 = conn.execute(stmt)

		# cluster only by resource
		resource_dict = {}
		resource_set_list = []
		rename_dict = {}
		# if a sock-fd arg call appears multiple times, record the first one
		visited_sock_dict = {}
		# record the exectime of each syscall
		exectime_dict = {}
		for syscall in cursor1:

			call_id = -1
			pid_num = ''
			count_num = ''
			total_num = ''
			exec_time = ''
			call_name = ''
			call_args = ''
			call_ret = ''
			if mode == 'trace':
				call_id = syscall[0]
				pid_num = syscall[6]
				exec_time = syscall[7]
				call_name = syscall[8]
				call_args = syscall[9]
				call_ret = syscall[10]
			elif mode == 'behavior':
				call_id = syscall[0]
				pid_num = syscall[4]
				count_num = syscall[5]
				total_num = syscall[6]
				exec_time = syscall[7]
				call_name = syscall[8]
				call_args = syscall[9]
				call_ret = syscall[10]

			behavior_id = -1
			level = ''
			pipe = ''
			comment = ''
			if mode == 'behavior':
				behavior_id = syscall[0]
				level = syscall[11]
				pipe = syscall[12]
				comment = syscall[13]

			syscall_tmp = [pid_num, call_name, call_args, call_ret]
			my_resource = []

			my_resource = get_resource(syscall_tmp)
			'''
			if level == 'partial':
				part_resource = comment.split(':')
				for i in range(len(part_resource)):
					if part_resource[i][0]=='\"' and \
						part_resource[i][-1] == '\"':
						part_resource[i] = part_resource[i][1:-1]
				my_resource = tuple(my_resource[i] + '(' + part_resource[i] \
					+ ')' for i in range(len(part_resource)))
			'''

			# if a sock-fd arg call appears multiple times 
			if len(my_resource) == 1:
				if call_name in mining.fd_func and ':' in my_resource[0]:
					if visited_sock_dict.has_key(call_name+my_resource[0]):
						continue
					else:
						visited_sock_dict[call_name+my_resource[0]] = True

			# for fcntl, the arg will decide the behavior
			if call_name == 'fcntl':
				if 'F_RDLCK' in call_args:
					call_name += '_rdlck'
				if 'F_UNLCK' in call_args:
					call_name += '_unlck'
				if 'F_WRLCK' in call_args:
					call_name += '_wrlck'

			my_syscall = (call_id, pid_num, behavior_id, pipe, count_num, \
				total_num, call_name) + my_resource

			# record the exectime of each syscall
			if not exectime_dict.has_key(my_syscall):
				exectime_dict[my_syscall] = exec_time

			# add syscall to the list of current resource
			if resource_dict.has_key(my_resource[0]):
				resource_dict[my_resource[0]] += [my_syscall]
			else:
				resource_dict[my_resource[0]] = [my_syscall]
				resource_set_list.append({my_resource[0]})

			if call_name == 'rename':
				# record rename relationship
				rename_dict[my_resource[0]] = my_resource[1]

				# we have added the call to the list of 'rename from'
				if not resource_dict.has_key(my_resource[1]):
					resource_dict[my_resource[1]] = []
					resource_set_list.append({my_resource[1]})

		if info[1] == 'synfigstudio' and mode == 'behavior' and info[3] == '8587':
			print resource_set_list
		# merge resource set
		set_list_num = len(resource_set_list)
		resource_set_flag = [0 for x in range(set_list_num)]
		for i in range(set_list_num):
			if resource_set_flag[i] == 1:
				continue

			# keep finding related resources
			fixed = False
			while not fixed:
				fixed = True
				for j in range(i+1, set_list_num):
					if resource_set_flag[j] == 1:
						continue

					# find the relationship of the sets
					merge = False
					for resource_i in resource_set_list[i]:
						if resource_i == '':
							continue
						for resource_j in resource_set_list[j]:
							if resource_j == '':
								continue

							# rename relationship
							if rename_dict.has_key(resource_i):
								if rename_dict[resource_i] == resource_j:
									merge = True
									break

							if rename_dict.has_key(resource_j):
								if rename_dict[resource_j] == resource_i:
									merge = True
									break

							# -journal
							if resource_i + '-journal' == resource_j:
								merge = True
								break

							if resource_j + '-journal' == resource_i:
								merge = True
								break

							# full path and relative path
							file_i = resource_i.split('/')[-1]
							file_j = resource_j.split('/')[-1]
							if file_i == file_j:
								if resource_i.endswith(resource_j):
									merge = True
									break

								if resource_j.endswith(resource_i):
									merge = True
									break

						if merge:
							break

					if merge:
						resource_set_list[i] = \
							resource_set_list[i].union(resource_set_list[j])
						resource_set_flag[j] = 1
						fixed = False
						break

		if info[1] == 'synfigstudio' and mode == 'behavior' and info[3] == '8587':
			print resource_set_list
			print resource_set_flag
		# collect calls of resources from one set
		for i in range(set_list_num):
			if resource_set_flag[i] == 1:
				continue

			call_list = []
			for resource in resource_set_list[i]:
				call_list += resource_dict[resource]

			time_call_list = []
			for call in call_list:
				time_call_list.append(tuple([exectime_dict[call]] + \
					[item for item in call]))

			time_call_list.sort(lambda x,y:cmp(x[0],y[0]))
			for i in range(len(time_call_list)):
				time_call_list[i] = list(time_call_list[i][1:])

			cluster_list += get_cluster(info, time_call_list)
		continue

		# the following clustering requires the calls as a sequence
		# examine each call site
		last_resource = ''
		last_syscalls = []
		cur_resource = ''
		cur_syscalls = []
		is_renamed = False
		# if a sock-fd arg call appears multiple times, record the first one
		visited_sock_dict = {}
		for syscall in cursor1:

			pid_num = ''
			count_num = ''
			total_num = ''
			call_name = ''
			call_args = ''
			call_ret = ''

			if mode == 'trace':
				pid_num = syscall[5]
				call_name = syscall[7]
				call_args = syscall[8]
				call_ret = syscall[9]
			elif mode == 'behavior':
				pid_num = syscall[3]
				count_num = syscall[4]
				total_num = syscall[5]
				call_name = syscall[7]
				call_args = syscall[8]
				call_ret = ''

			if call_name not in mining.key_func:
				continue

			behavior_id = -1
			level = ''
			pipe = ''
			comment = ''
			if mode == 'behavior':
				behavior_id = syscall[0]
				level = syscall[9]
				pipe = syscall[10]
				comment = syscall[11]

			syscall_tmp = [pid_num, call_name, call_args, call_ret]
			my_resource = []
			if level != 'partial':
				my_resource = get_resource(syscall_tmp)
			else:
				my_resource = comment.split(':')
				for i in range(len(my_resource)):
					if my_resource[i][0]=='\"' and my_resource[i][-1]=='\"':
						my_resource[i] = my_resource[i][1:-1]

			# if a call appears continuously, only record the first time 
			if my_resource == cur_resource and \
				call_name == cur_syscalls[-1][4]:
				continue

			# if a sock-fd arg call appears multiple times 
			if len(my_resource) == 1:
				if call_name in mining.fd_func and ':' in my_resource[0]:
					if visited_sock_dict.has_key(call_name+my_resource[0]):
						continue
					else:
						visited_sock_dict[call_name+my_resource[0]] = True

			# for fcntl, the arg will decide the behavior
			if call_name == 'fcntl':
				if 'F_RDLCK' in call_args:
					call_name += '_rdlck'
				if 'F_UNLCK' in call_args:
					call_name += '_unlck'
				if 'F_WRLCK' in call_args:
					call_name += '_wrlck'

			my_syscall = [pid_num, behavior_id, pipe, count_num, \
				total_num, call_name] + my_resource
			# if rename
			if len(my_resource) == 2:
				# rename the last two resources
				if (is_equal(my_resource[1], cur_resource) and \
					is_equal(my_resource[0], last_resource)) or \
					(is_equal(my_resource[0], cur_resource) and \
					is_equal(my_resource[1], last_resource)):
					cur_syscalls += [my_syscall]
					last_syscalls += [my_syscall]
				else:
					new_resource = ''
					if is_equal(my_resource[0], cur_resource):
						new_resource = my_resource[1]
					elif is_equal(my_resource[1], cur_resource):
						new_resource = my_resource[0]

					# both resources of rename are new
					if new_resource == '':
						if is_renamed:
							cluster_list += get_cluster(info, \
								last_syscalls + cur_syscalls)
						else:
							cluster_list += get_cluster(info, last_syscalls)
							cluster_list += get_cluster(info, cur_syscalls)
						last_resource = my_resource[0]
						last_syscalls = [my_syscall]
						cur_resource = my_resource[1]
						cur_syscalls = [my_syscall]
					# one resource of rename is new
					else:
						cluster_list += get_cluster(info, last_syscalls)
						last_resource = cur_resource
						last_syscalls = cur_syscalls + [my_syscall]
						cur_resource = new_resource
						cur_syscalls = [my_syscall]
				is_renamed = True

			# not rename
			elif len(my_resource) == 1:

				if is_equal(my_resource[0], cur_resource):
					cur_syscalls += [my_syscall]
				#elif is_equal(my_resource[0], last_resource):
				#	last_syscalls += [my_syscall]
				else:
					# update resource
					if is_renamed:
						cluster_list += get_cluster(info, \
							last_syscalls + cur_syscalls)
						last_resource = ''
						last_syscalls = []
					else:
						cluster_list += get_cluster(info, last_syscalls)
						last_resource = cur_resource
						last_syscalls = cur_syscalls

					cur_resource = my_resource[0]
					cur_syscalls = [my_syscall]
					is_renamed = False

		if is_renamed:
			cluster_list += get_cluster(info, last_syscalls + cur_syscalls)
		else:
			cluster_list += get_cluster(info, last_syscalls)
			cluster_list += get_cluster(info, cur_syscalls)

	return cluster_list


def do_clustering():

	# get cluster from exit_traces
	trace_cluster_list = get_cluster_list('trace')

	# get cluster from exit_behavior
	behavior_cluster_list = get_cluster_list('behavior')

	# get pattern from trace_cluster_list
	cluster_pattern_list = get_pattern(trace_cluster_list)
	#for pattern in cluster_pattern_list:
	#	print pattern

	# store clusters into database
	domain = ''
	project = ''
	test_case = ''
	pid_num = ''
	pipe = ''
	support = ''
	pattern_id = -1
	pattern_db = ''
	resource_x = ''
	resource_y = ''
	resource_z = ''
	behavior_ids = ''
	for line in behavior_cluster_list:
		if 'Pattern' in line:
			if project != '':
				row = [domain, project, test_case, pid_num, behavior_ids, \
					pipe, support, pattern_id, pattern_db, resource_x, \
					resource_y, resource_z]
				insert_cluster(row)
				resource_x = ''
				resource_y = ''
				resource_z = ''

			pattern = line.strip()
			pattern_str = remove_loop(pattern)
			pattern_db = pattern_str
			if not pattern_str in cluster_pattern_list:
				pattern_id = -1
			else:
				pattern_id = cluster_pattern_list.index(pattern_str)

		if 'Behavior_id: ' in line:
			behavior_ids = line[len('Behavior_id: '):]

		if 'Pipe: ' in line:
			pipe = line[len('Pipe: '):]

		if 'PID: ' in line:
			pid_num = line[len('PID: '):]

		if 'Support: ' in line:
			support = line[len('Support: '):]

		if 'Resource' in line:
			if ' x: ' in line:
				resource_x = line[len('Resource x: '):]
			if ' y: ' in line:
				resource_y = line[len('Resource y: '):]
			if ' z: ' in line:
				resource_z = line[len('Resource z: '):]

		if 'Info' in line:
			info = line.split()
			domain = info[1]
			project = info[2]
			test_case = info[3]

	row = [domain, project, test_case, pid_num, behavior_ids, pipe, support, \
		pattern_id, pattern_db, resource_x, resource_y, resource_z]
	insert_cluster(row)

# if in clustering step
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
	do_clustering()
	conn.commit()
	conn.close()
