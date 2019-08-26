import os
import sys
import getopt
from sqlite3 import connect


# usage of this script
def usage():
	print '%s: clean trace files and genarate a database file'%sys.argv[0]
	print 'Usage:'
	print '\tpython %s [-t <traces_dir>] [-d <database_dir>]'%sys.argv[0]
	print '\tpython %s [-h]'%sys.argv[0]
	print 'Options:'
	print '\t-t specify the path to the traces directory (default ./traces)'
	print '\t-d specify the path to the output database (default ./traces.db)'
	print '\t-h print help messages'


# helper function to store trace data into database
def insert_trace(row):
	stmt = "INSERT INTO traces (Domain, Project, Testcase, Epoch, Signal, \
		PID, ExecTime, CallName, CallArgs, CallRet) VALUES \
		(?,?,?,?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create trace table
def create_trace():
	conn.execute("DROP TABLE IF EXISTS traces")
	stmt = "CREATE TABLE traces (ID INTEGER PRIMARY KEY AUTOINCREMENT, \
		Domain, Project, Testcase, Epoch, Signal, PID, \
		ExecTime, CallName, CallArgs, CallRet)"
	conn.execute(stmt)
	conn.execute("CREATE INDEX IF NOT EXISTS trace_index ON traces(ID)")


# helper function to store stoptime data into database
def insert_time(row):
	stmt = "INSERT INTO stoptime (Domain, Project, Testcase, Epoch, Signal, \
		Workloadtime, Stoptime, Cleantime, Lastcmdtime) VALUES \
		(?,?,?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create stoptime table
def create_time():
	conn.execute("DROP TABLE IF EXISTS stoptime")
	stmt = "CREATE TABLE stoptime (ID INTEGER PRIMARY KEY AUTOINCREMENT, \
		Domain, Project, Testcase, Epoch, Signal, \
		Workloadtime, Stoptime, Cleantime, Lastcmdtime)"
	conn.execute(stmt)
	conn.execute("CREATE INDEX IF NOT EXISTS stoptime_index ON stoptime(ID)")


# helper function to store process relationship data into database
def insert_proc(row):
	stmt = "INSERT INTO procship (Domain, Project, Testcase, Epoch, Signal, \
		PPID, PID) VALUES (?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create process relationship table
def create_proc():
	conn.execute("DROP TABLE IF EXISTS procship")
	stmt = "CREATE TABLE procship (ID INTEGER PRIMARY KEY AUTOINCREMENT, \
		Domain, Project, Testcase, Epoch, Signal, PPID, PID)"
	conn.execute(stmt)
	conn.execute("CREATE INDEX IF NOT EXISTS procship_index ON procship(ID)")


# helper function to store thread info into database
def insert_thread(row):
	stmt = "INSERT INTO threads (Domain, Project, Testcase, Epoch, Signal, \
		PID, TID) VALUES (?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create thread info table
def create_thread():
	conn.execute("DROP TABLE IF EXISTS threads")
	stmt = "CREATE TABLE threads (ID INTEGER PRIMARY KEY AUTOINCREMENT, \
		Domain, Project, Testcase, Epoch, Signal, PID, TID)"
	conn.execute(stmt)
	conn.execute("CREATE INDEX IF NOT EXISTS threads_index ON threads(ID)")


# helper function to store open fd info into database
def insert_openfd(row):
	stmt = "INSERT INTO openfd (Domain, Project, Testcase, Epoch, Signal, \
		CMD, PID, TID, USER, FD, MODE, TYPE, DEV, SIZEOFF, NODE, NAME) \
		VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create openfd info table
def create_openfd():
	conn.execute("DROP TABLE IF EXISTS openfd")
	stmt = "CREATE TABLE openfd (ID INTEGER PRIMARY KEY AUTOINCREMENT, \
		Domain, Project, Testcase, Epoch, Signal, CMD, PID, TID, USER, \
		FD, MODE, TYPE, DEV, SIZEOFF, NODE, NAME)"
	conn.execute(stmt)
	conn.execute("CREATE INDEX IF NOT EXISTS openfd_index ON openfd(ID)")


# get open fd list
def analyze_openfd_file(openfd_dir):

	# read openfd file
	openfd_file = open(openfd_dir, 'r')
	lines = openfd_file.readlines()

	# parse lsof output
	first_line = lines[0]

	end_pid  = first_line.find('PID')    + 3
	end_tid  = first_line.find('TID')    + 3
	end_user = first_line.find('USER')   + 4
	end_fd   = first_line.find('FD')     + 2
	end_mode = first_line.find('FD')     + 5
	end_type = first_line.find('TYPE')   + 4
	end_dev  = first_line.find('DEVICE') + 6
	end_soff = first_line.find('OFF')    + 3
	end_node = first_line.find('NODE')   + 4

	for line in lines:
		cmd  = line[:end_pid].split()[0].strip()
		pid  = line[:end_pid].split()[1].strip()
		tid  = line[end_pid:end_tid].strip()
		user = line[end_tid:end_user].strip()
		fd   = line[end_user:end_fd].strip()
		mode = line[end_fd:end_mode].strip()
		typ  = line[end_mode:end_type].strip()
		dev  = line[end_type:end_dev].strip()
		soff = line[end_dev:end_soff].strip()
		node = line[end_soff:end_node].strip()
		name = line[end_node:].strip()

		row  = [domain, project, testcase, epoch, signal]
		row += [cmd, pid, tid, user, fd, mode, typ, dev, soff, node, name]
		if cmd != 'COMMAND':
			insert_openfd(row)

# get stop time of test cases from runtime.log
def analyze_log_file(log_dir):

	# read log file
	log_file = open(log_dir, 'r')
	lines = log_file.readlines()

	signal = ''
	lastcmdtime = ''
	for line in lines:
		line = line.strip()

		# update current signal number
		if 'Signal:' in line:
			signal = line.split()[1]

		if 'root' in line:
			lastcmdtime = line.split()[1]

		# record stop time and clean time for each test case
		if 'timestamp:' in line:
			workload = line.split()[2]
			stoptime = line.split()[4]
			cleantime = line.split()[6]
			row_data = [domain, project, testcase, epoch, signal, workload, \
				stoptime, cleantime, lastcmdtime]
			insert_time(row_data)
			
		# record process-relationship
		if 'echo \"pid' in line:
			line = line.replace('pid ','')
			ship_str = line[line.find('echo') + 5:]
			if len(ship_str) <= 4:
				continue
			ship_list = ship_str[2:-2].split(',')
			for ship in ship_list:
				ship = ship.strip()
				if len(ship) <= 2:
					continue
				mppid, mpid = ship[1:-1].split(':')
				if len(mppid) > 0 and len(mpid) > 0:
					row_data = [domain, project, testcase, epoch, signal, \
						mppid, mpid]
					insert_proc(row_data)
			
		# record threads info
		if 'echo \"tid' in line:
			line = line.replace('tid ','')
			thread_str = line[line.find('echo') + 5:]
			if len(thread_str) <= 4:
				continue
			thread_list = thread_str[2:-2].split(',')
			for thread in thread_list:
				thread = thread.strip()
				if len(thread) <= 2:
					continue
				mpid, mtid = thread[1:-1].split(':')
				if len(mpid) > 0 and len(mtid) > 0:
					row_data = [domain, project, testcase, epoch, signal, \
						mpid, mtid]
					insert_thread(row_data)


# get system-call info from each trace file
def analyze_trace_file(trace_dir):
	#print domain, project, testcase, epoch, signal, pid
	
	# read trace file
	trace_file = open(trace_dir, 'r')
	lines = trace_file.readlines()
	for line in lines:
		if ' > ' in line:
			continue

		line = line.strip()
		seg = line.split()
		if len(seg) < 2:
			continue

		# get time stamp and call string
		timestamp = seg[0]
		call_str = line[line.find(seg[1]) + len(seg[1]) + 1:]

		# get call name, call args and call return
		call_name = ''
		call_args = ''
		call_ret = ''
		# for '--- SIGxxx {si_sig...'
		if '--- SIG' in line:
			call_name = call_str.split()[1]
			args_start_loc = call_str.find(call_name)
			call_args = call_str[args_start_loc + len(call_name) + 1:-4]
			call_ret = 'null'
		# for '+++ exited with x +++'
		elif '+++ exited' in line:
			call_name = 'exited'
			call_args = call_str[len('+++ exited with '):-4]
			call_ret = 'null'
		# for '+++ killed by xxxx +++'
		elif '+++ killed' in line:
			call_name = 'killed'
			call_args = call_str[len('+++ killed by '):-4]
			call_ret = 'null'
		# for normal system calls
		else:
			# get the range of args in call string
			args_start_loc = 0
			args_stop_loc = len(call_str)
			paren_cnt = 0
			quoted = False
			for i in range(len(call_str)):
				# for "xxxxx(xxx" in args, the paren should not be counted
				if call_str[i] == '\"':
					# for "xxxx\"xxxx", "xxxx\\"
					slashed = False
					for j in reversed(range(i)):
						if call_str[j] == '\\':
							slashed = not slashed
						else:
							break
					if not slashed:
						quoted = not quoted
				if quoted:
					continue
				# count for '(' and ')'
				if call_str[i] == '(':
					if paren_cnt == 0:
						args_start_loc = i
					paren_cnt += 1
				if call_str[i] == ')':
					paren_cnt -= 1
					if paren_cnt == 0:
						args_stop_loc = i
						break

			# get call name, call args and call return
			call_name = call_str[:args_start_loc]
			call_args = call_str[args_start_loc + 1: args_stop_loc]
			call_ret = call_str[args_stop_loc + 4:]

			if '<unfinished ...>' in line or \
					'<ptrace(SYSCALL):No such process' in line:
				call_ret = 'unfinished'

		# insert all info to database
		row_data = [domain, project, testcase, epoch, signal, pid, \
					timestamp, call_name, call_args, call_ret]
		insert_trace(row_data)
	trace_file.close()


def do_cleaning():

	# create tables
	create_proc()
	create_thread()
	create_trace()
	create_time()
	create_openfd()

	global domain
	global project
	global testcase
	global epoch
	global signal
	global pid

	if not os.path.isdir(traces_dir):
		sys.stderr.write('Invalid path!\n')
		sys.exit(1)

	# get general info of each test case
	# domain level
	for domain_name in os.listdir(traces_dir):
		domain = domain_name
		domain_dir = os.path.join(traces_dir, domain_name)
		if not os.path.isdir(domain_dir):
			continue

		# project level
		for project_name in os.listdir(domain_dir):
			project = project_name
			project_dir = os.path.join(domain_dir, project_name)
			if not os.path.isdir(project_dir):
				continue

			# test case level
			for testcase_name in os.listdir(project_dir):
				testcase = testcase_name
				testcase_dir = os.path.join(project_dir, testcase_name)
				if not os.path.isdir(testcase_dir):
					continue

				# epoch level
				for epoch_name in os.listdir(testcase_dir):
					epoch = epoch_name
					epoch_dir = os.path.join(testcase_dir, epoch_name)
					if not os.path.isdir(epoch_dir):
						continue

					# signal level
					for trace_file in os.listdir(epoch_dir):
						signal,pid = trace_file.split('.')[0:2]
						trace_dir = os.path.join(epoch_dir, trace_file)
						if signal.isdigit() and pid.isdigit():
							analyze_trace_file(trace_dir)
							pass
						if trace_file == 'runtime.log':
							analyze_log_file(trace_dir)
							pass
						if 'openfd.log' in trace_file:
							analyze_openfd_file(trace_dir)
							pass


# if in cleaning step
if __name__ == "__main__":

	# global variables for command line arguments
	global traces_dir
	global conn

	# parse command line options
	traces_dir = './traces'
	database_dir = './traces.db'
	opts, args = getopt.getopt(sys.argv[1:], 't:d:h')
	for op, value in opts:
		if op == '-t':
			traces_dir = value
		if op == '-d':
			database_dir = value
		if op == '-h':
			usage()
			sys.exit(0)

	conn = connect(database_dir)
	conn.text_factory = str
	do_cleaning()
	conn.commit()
	conn.close()
