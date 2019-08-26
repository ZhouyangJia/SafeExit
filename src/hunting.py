import os
import sys
import getopt
import mining
from sqlite3 import connect


# usage of this script
def usage():
	print '%s: hunt missing behaviors/clusters in signal tests'%sys.argv[0]
	print 'Usage:'
	print '\tpython %s [-d <database_dir>]'%sys.argv[0]
	print '\tpython %s [-h]'%sys.argv[0]
	print 'Options:'
	print '\t-d specify the path of database'
	print '\t-h print help messages'


# helper function to store miss_behavior into database
def insert_missbehavior(row):
	stmt = "INSERT INTO miss_behavior (Domain, Project, BehaviorID, Testcase, \
		SIGHUP, SIGINT, SIGQUIT, SIGILL, SIGTRAP, SIGABRT, SIGBUS, SIGFPE, \
		SIGKILL, SIGUSER1, SIGSEGV, SIGUSER2, SIGPIPE, SIGALRM, SIGTERM, \
		SIGSTKFLT, SIGCHLD, SIGCONT, SIGSTOP, SIGTSTP, SIGTTIN, SIGTTOU,\
		SIGURG, SIGXCPU, SIGXFSZ, SIGVTALRM, SIGPROF, SIGWINCH, SIGPOLL, \
		SIGPWR, SIGSYS) \
		VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,\
		?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create miss_behavior table
def create_missbehavior():
	conn.execute("DROP TABLE IF EXISTS miss_behavior")
	stmt = "CREATE TABLE miss_behavior (ID INTEGER PRIMARY KEY AUTOINCREMENT,\
		Domain, Project, BehaviorID, Testcase, \
		SIGHUP, SIGINT, SIGQUIT, SIGILL, SIGTRAP, SIGABRT, SIGBUS, SIGFPE, SIGKILL, \
		SIGUSER1, SIGSEGV, SIGUSER2, SIGPIPE, SIGALRM, SIGTERM, \
		SIGSTKFLT, SIGCHLD, SIGCONT, SIGSTOP, SIGTSTP, SIGTTIN, SIGTTOU,\
		SIGURG, SIGXCPU, SIGXFSZ, SIGVTALRM, SIGPROF, SIGWINCH, SIGPOLL, \
		SIGPWR, SIGSYS)"
	conn.execute(stmt)
	stmt = "CREATE INDEX IF NOT EXISTS missbehavior_index ON miss_behavior(ID)"
	conn.execute(stmt)


# helper function to store miss_cluster into database
def insert_misscluster(row):
	stmt = "INSERT INTO miss_cluster (Domain, Project, ClusterID, Testcase, \
		SIGHUP, SIGINT, SIGQUIT, SIGILL, SIGTRAP, SIGABRT, SIGBUS, SIGFPE, \
		SIGKILL, SIGUSER1, SIGSEGV, SIGUSER2, SIGPIPE, SIGALRM, SIGTERM, \
		SIGSTKFLT, SIGCHLD, SIGCONT, SIGSTOP, SIGTSTP, SIGTTIN, SIGTTOU,\
		SIGURG, SIGXCPU, SIGXFSZ, SIGVTALRM, SIGPROF, SIGWINCH, SIGPOLL, \
		SIGPWR, SIGSYS) \
		VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,\
		?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
	conn.execute(stmt, (row))


# create miss_cluster table
def create_misscluster():
	conn.execute("DROP TABLE IF EXISTS miss_cluster")
	stmt = "CREATE TABLE miss_cluster (ID INTEGER PRIMARY KEY AUTOINCREMENT,\
		Domain, Project, ClusterID, Testcase, SIGHUP, SIGINT, SIGQUIT, \
		SIGILL, SIGTRAP, SIGABRT, SIGBUS, SIGFPE, SIGKILL, \
		SIGUSER1, SIGSEGV, SIGUSER2, SIGPIPE, SIGALRM, SIGTERM, \
		SIGSTKFLT, SIGCHLD, SIGCONT, SIGSTOP, SIGTSTP, SIGTTIN, SIGTTOU,\
		SIGURG, SIGXCPU, SIGXFSZ, SIGVTALRM, SIGPROF, SIGWINCH, SIGPOLL, \
		SIGPWR, SIGSYS)"
	conn.execute(stmt)
	stmt = "CREATE INDEX IF NOT EXISTS misscluster_index ON miss_cluster(ID)"
	conn.execute(stmt)


def do_hunting():

	create_missbehavior()
	create_misscluster()

	# collect test cases of each project
	proj_dict = {}
	stmt = "SELECT DISTINCT Project, Testcase, Epoch FROM exit_traces \
		WHERE Epoch like '%signal%'"
	cursor = conn.execute(stmt)
	for row in cursor:
		print row
		project = row[0]
		test_case = row[1]
		if not proj_dict.has_key(project):
			proj_dict[project] = [test_case]
		else:
			proj_dict[project].append(test_case)
	print proj_dict
	# confirm behaviors
	stmt = "SELECT * FROM exit_behavior"
	miss_behaviors = [{}]
	cursor = conn.execute(stmt)
	for row in cursor:
		ID = row[0]
		domain = row[2]
		project = row[3]
		test_case = row[4]
		support = row[6]
		total = row[7]
		miss_behavior = {}
		if support != total:
			miss_behaviors.append(miss_behavior)
			continue
		[call_name, call_args, call_ret, level, pid_pipe] = row[9:14]
		print 'Now hunting for behavior %d: %s %s %s %s %s ...' \
			%(ID, project, test_case, level, call_name, call_args.split(',')[0])
		if not proj_dict.has_key(project):
			miss_behaviors.append(miss_behavior)
			continue
		testcase_list = proj_dict[project]
		for test_case in testcase_list:

			# confirm behaviors for each signal
			miss_behavior[test_case] = [0 for x in range(32)]
			print '%s:'%(test_case),
			mining.conn = conn
			for signal in range(32):
				res,support = mining.confirm_behavior(project, test_case, \
					['signal_epoch_0'], signal, call_name, call_args, pid_pipe)
				if len(res) and support:
					if 'complete' in str(res) or level in str(res):
						miss_behavior[test_case][signal] = 1
				print '%d(%d)'%(signal, miss_behavior[test_case][signal]),
			print

		miss_behaviors.append(miss_behavior)
		# print miss behaviors
		#result_file.write('Behavior %d: %s %s %s %s ...\n' \
		#	%(ID, project, level, call_name, call_args.split(',')[0]))
		for test_case in sorted(miss_behavior.keys()):
			#result_file.write(str(miss_behavior[test_case][1:])+'\n')
			row = [domain, project, ID, test_case]
			row += miss_behavior[test_case][1:]
			insert_missbehavior(row)

	#result_file.write('\n')
	print
	# confirm clusters
	stmt = "SELECT * FROM exit_cluster"
	cursor = conn.execute(stmt)
	for row in cursor:
		ID = row[0]
		domain = row[1]
		project = row[2]
		test_case = row[3]
		pid_num = row[4]
		behavior_id = row[5]
		support = row[7]
		pattern = row[9]
		res_x = row[10]
		res_y = row[11]
		res_z = row[11]

		if support != 'True':
			continue

		if 'exit_group' in pattern:
			continue

		print 'Now hunting for cluster %d: %s %s %s %s %s' \
			%(ID, project, pattern[3:], res_x, res_y, res_z)

		miss_cluster = {}
		if not proj_dict.has_key(project):
			continue
		test_case_list = proj_dict[project]
		for test_case in sorted(test_case_list):
			miss_cluster[test_case] = [0 for x in range(32)]
			print '%s:'%(test_case),
			for signal in range(32):
				all_found = True
				all_miss = True
				for id in behavior_id.split():
					#print len(miss_behaviors), int(id),miss_behaviors[int(id)]
					if miss_behaviors[int(id)][test_case][signal] == 1:
						all_miss = False
					else:
						all_found = False
				if all_found:
					miss_cluster[test_case][signal] = 2
				if all_miss:
					miss_cluster[test_case][signal] = 0
				if not all_miss and not all_found:
					miss_cluster[test_case][signal] = 1
				print '%d(%d)'%(signal, miss_cluster[test_case][signal]),
			print

		# print miss clusters
		#result_file.write('Cluster %d: %s %s %s %s %s\n' \
		#	%(ID, project, pattern[3:], res_x, res_y, res_z))
		for test_case in sorted(miss_cluster.keys()):
			#result_file.write(str(miss_cluster[test_case][1:])+'\n')
			row = [domain, project, ID, test_case]
			row += miss_cluster[test_case][1:]
			insert_misscluster(row)


# if in hunting step
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
	do_hunting()
	conn.commit()
	conn.close()
