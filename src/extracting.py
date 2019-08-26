import os
import sys
import mining
import getopt
from sqlite3 import connect


# usage of this script
def usage():
	print '%s: extract sub-traces of exit phase'%sys.argv[0]
	print 'Usage:'
	print '\tpython %s [-d <database_dir>]'%sys.argv[0]
	print '\tpython %s [-h]'%sys.argv[0]
	print 'Options:'
	print '\t-d specify the path of database'
	print '\t-h print help messages'


# get pid-tid relationship in given test case
def get_piddir(test_case, signal):
	get_pid = {}
	stmt = "SELECT PID, TID from threads where \
		Testcase == '%s' and Signal = '%s'"%(test_case, signal)
	cursor = conn.execute(stmt)
	for row in cursor:
		mpid = str(row[0])
		mtid = str(row[1])
		get_pid[mtid] = mpid
	return get_pid


# helper function to store process relationship data into database
def insert_proc(row):
	stmt = "INSERT INTO procship (Domain, Project, Testcase, Epoch, Signal, \
		PPID, PID) VALUES (?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# helper function to store thread info into database
def insert_thread(row):
	stmt = "INSERT INTO threads (Domain, Project, Testcase, Epoch, Signal, \
		PID, TID) VALUES (?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# helper function to store trace data into database
def insert_trace(row):
	stmt = "INSERT INTO exit_traces (Domain, Project, Testcase, Epoch, \
		Signal, PID, ExecTime, CallName, CallArgs, CallRet) \
		VALUES (?,?,?,?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create trace table
def create_trace():
	conn.execute("DROP TABLE IF EXISTS exit_traces")
	stmt = "CREATE TABLE exit_traces (ID INTEGER PRIMARY KEY AUTOINCREMENT,\
		Domain, Project, Testcase, Epoch, Signal, PID, \
		ExecTime, CallName, CallArgs, CallRet)"
	conn.execute(stmt)
	stmt = "CREATE INDEX IF NOT EXISTS exittrace_index ON exit_traces(ID)"
	conn.execute(stmt)


# add process relationship for clone/fork
def add_proc(row):
	
	[domain, project, testcase, epoch, signal, PID, exectime, \
		call_name, call_args, call_ret] = row

	get_tgid_dir = get_piddir(testcase, signal)
	tgid = ''
	if get_tgid_dir.has_key(PID):
		tgid = get_tgid_dir[PID]

	child_pid = ''
	thread_id = ''
	if call_name == 'fork':
		child_pid = call_ret
	if call_name == 'clone':
		if 'CLONE_THREAD' in call_args:
			thread_id = call_ret
		else:
			child_pid = call_ret

	if child_pid != '':
		row = [domain, project, testcase, epoch, signal, child_pid, child_pid]
		insert_thread(row)
		conn.commit()
		row = [domain, project, testcase, epoch, signal, tgid, child_pid]
		insert_proc(row)
		conn.commit()

	if thread_id != '':
		row = [domain, project, testcase, epoch, signal, tgid, thread_id]
		insert_thread(row)
		conn.commit()

# whether a call is necessary or not
# select key arguments of system calls
def is_necessary(syscall):

	# dereference infomation in row
	[domain, project, testcase, epoch, signal, pid_num, \
		exec_time, call_name, call_args, call_ret] = syscall
	args = call_args.split(',')

	# skip failed calls
	if '-1 ' in call_ret:
		return False

	# filter out unnesessary futex calls
	if call_name == 'futex':
		if 'PRIVATE' in args[1]:
			return False
		iswakeflag = False
		for wake_word in ['WAKE', 'REQUEUE', 'UNLOCK']:
			if wake_word in args[1]:
				iswakeflag = True
				break
		if not iswakeflag:
			return False

	# filter out unnesessary open calls
	if call_name == 'open':
		if 'O_CREAT' not in args[1]:
			return False

	# filter out unnesessary openat calls
	if call_name == 'openat':
		if 'O_CREAT' not in args[2]:
			return False

	# filter out unnesessary '/dev/null' ops
	if '/dev/null' in args[0]:
		return False

	# filter out unnesessary fcntl calls
	if call_name == 'fcntl':
		if 'F_OFD_SETLK' not in call_args and 'F_SETLK' not in call_args :
			return False

	return True

def do_extracting():

	# create trace table
	create_trace()

	# select traces between stoptime and cleantime
	stmt = '''
		SELECT traces.Domain, traces.Project, traces.Testcase, traces.Epoch, 
			traces.Signal, traces.PID, traces.ExecTime, traces.CallName, 
			traces.CallArgs, traces.CallRet
		FROM traces, stoptime
		WHERE 
			traces.Testcase == stoptime.Testcase AND
			traces.Epoch == stoptime.Epoch AND
			traces.Signal == stoptime.Signal AND
			traces.ExecTime > stoptime.Stoptime AND
			traces.ExecTime < stoptime.Cleantime
		'''
			#traces.ExecTime > stoptime.Workloadtime AND
			#traces.ExecTime < stoptime.Stoptime
	cursor = conn.execute(stmt)
	# if a call appears multiple times, only record the first time
	syscall_dict = {}
	# if a call appears continuously, only record the first time
	syscall_last = ''
	for row in cursor:
		[domain, project, testcase, epoch, signal, pid_num, \
			exec_time, call_name, call_args, call_ret] = row

		if call_name == 'clone' or call_name == 'fork':
			add_proc(row)
		if call_name in mining.key_func and is_necessary(row):

			syscall_now =  pid_num + call_name + call_args
			args = call_args.split(',')
			if call_name in mining.output_func:
				syscall_now =  pid_num + call_name + args[0]
			if syscall_dict.has_key(syscall_now):
				continue
			else:
				syscall_dict[syscall_now] = True

			insert_trace(row)


# if in extracting step
if __name__ == "__main__":

	global conn

	# parse command line options
	database_dir = './traces.db'
	append_mode = False
	opts, args = getopt.getopt(sys.argv[1:], 'd:h')
	for op, value in opts:
		if op == '-d':
			database_dir = value
		if op == '-h':
			usage()
			sys.exit(0)

	conn = connect(database_dir)
	conn.text_factory = str
	do_extracting()
	conn.commit()
	conn.close()
