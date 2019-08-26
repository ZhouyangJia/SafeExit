import os
import sys
import getopt
from sqlite3 import connect

from sklearn import tree
from sklearn.preprocessing import OneHotEncoder
import pydotplus
import collections

from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import f1_score
from sklearn.metrics import accuracy_score
from sklearn.metrics import balanced_accuracy_score
from sklearn.metrics import precision_recall_fscore_support
import numpy as np
import statistics


# usage of this script
def usage():
	print '%s: predicting exit behavior under given environment'%sys.argv[0]
	print 'Usage:'
	print '\tpython %s [-d <train_database_dir>]'%sys.argv[0]
	print '\tpython %s [-e <train_env_file>]'%sys.argv[0]
	print '\tpython %s [-t <test_database_dir>]'%sys.argv[0]
	print '\tpython %s [-f <test_env_file>]'%sys.argv[0]
	print '\tpython %s [-h]'%sys.argv[0]
	print 'Options:'
	print '\t-d specify the path of train database'
	print '\t-d specify the path of train environment file'
	print '\t-t specify the path of test database'
	print '\t-f specify the path of test environment file'
	print '\t-h print help messages'


# get signature of a syscall
def get_sign(call_info):
	[call_name, call_args, call_ret, levle, pipe, \
		arg1, arg2, arg3, comment] = call_info

	partial_names = ['binlog', 'smplayer.ini.', 'hdpi.ini.', 'playlist.ini.', \
		'smplayer/.', 'c69906077557f5c3.ini.', 'file_settings/c/.']
	for partial_name in partial_names:
		if partial_name in arg1:
			arg1 = arg1[:arg1.rfind('.')]
		if partial_name in arg2:
			arg2 = arg2[:arg2.rfind('.')]

	if 'NETLINK' in arg1:
		arg1 = arg1[:arg1.rfind(':')]

	if levle == 'partial':
		return call_name + '_' + pipe + '_' + comment
	if call_name in ['kill', 'exit_group']:
		return call_name + '_' + pipe
	elif call_name in ['write', 'writev', 'pwrite64', 'sendmsg']:
		if ':' in arg1:
			return call_name + '_' + pipe
		else:
			return call_name + '_' + arg1 + '_' + pipe
	elif call_name in ['sendto']:
		pipe = pipe[:pipe.find(':')]
		return call_name + '_' + pipe
	elif call_name in ['ftruncate', 'fdatasync', 'creat', 'fcntl', 'fsync' \
			,'bind', 'flock', 'unlink']:
		return call_name + '_' + arg1 + '_' + pipe
	elif call_name in ['openat']:
		return call_name + '_' + arg2 + '_' + pipe
	elif call_name in ['rename']:
		return call_name + '_' + arg1 + '_' + arg2 + '_' + pipe
	else:
		print call_info
		exit('New call_name')


# main entrance of predicting
def do_predicting():
	# get project list
	project_list = []
	stmt = "SELECT DISTINCT Project FROM exit_behavior"
	cursor = conn.execute(stmt)
	for row in cursor:
		project_list.append(row[0])

	# for each project
	for project in project_list:

		# get testcase list of training samples
		testcase_list = []
		stmt = "SELECT DISTINCT Testcase FROM exit_behavior \
			WHERE Project = '%s'"%project
		cursor = conn.execute(stmt)
		for row in cursor:
			testcase_list.append(row[0])
		testcase_num = len(testcase_list)

		# for each syscall in training samples, get its labels
		call_labels_list = []
		call_index_dict = {}
		call_index_dict_cnt = 0
		# also, we will put syscalls in different sets
		all_syscall_set = set()
		general_syscall_set = set()
		specific_syscall_set = set()
		# collect all syscalls from training samples
		stmt = "SELECT Testcase, CallName, CallArgs, CallRet, Level, PIPE, \
			Arg1, Arg2, Arg3, Comment FROM exit_behavior WHERE \
			Support == Total and not Testcase == 'sample_0'"
		cursor = conn.execute(stmt)
		for row in cursor:
			testcase = row[0]
			call_sign = get_sign(list(row[1:]))
			all_syscall_set.add(call_sign)
			# sample_0 means empty workload and default config
			# we put syscalls of this sample into general_syscall_set
			#if testcase == 'sample_0':
				#general_syscall_set.add(call_sign)
			# indexing new syscall
			if not call_index_dict.has_key(call_sign):
				call_labels_list.append([0 for x in range(testcase_num)])
				call_index_dict[call_sign] = call_index_dict_cnt
				call_index_dict_cnt += 1
			index = call_index_dict[call_sign]

			testcase_id = int(testcase.split('_')[-1])
			# mark the label as 1, if the syscall appears in this sample
			call_labels_list[index][testcase_id] = 1

		specific_syscall_set = all_syscall_set - general_syscall_set

		# different syscalls may have exactly the same labels
		# in this case, we do not need to build different trees for them
		# so, we cluster labels to labelsgroup
		call_labelsgroup_dict = {}
		labels_group_list = []
		labels_index_dict = {}
		labels_index_dict_cnt = 0
		for syscall in sorted(list(specific_syscall_set)):
			index = call_index_dict[syscall]
			labels_sign = str(call_labels_list[index])
			if not labels_index_dict.has_key(labels_sign):
				labels_group_list.append(call_labels_list[index])
				labels_index_dict[labels_sign] = labels_index_dict_cnt
				labels_index_dict_cnt += 1
			call_labelsgroup_dict[syscall] = labels_index_dict[labels_sign]

		# get training feature
		env_fd = open(env_file, 'r')
		env_lines = env_fd.readlines()
		feature_names = env_lines[0].strip().split('\t')
		train_X = env_lines[1:]
		for i in range(len(train_X)):
			train_X[i] = train_X[i].strip().split('\t')
		env_fd.close()

		# get test feature
		test_env_fd = open(test_env_file, 'r')
		test_env_lines = test_env_fd.readlines()
		test_X = test_env_lines[1:]
		for i in range(len(test_X)):
			test_X[i] = test_X[i].strip().split('\t')
		test_env_fd.close()
		test_number = len(test_X)

		# for each syscall in test samples, get its labels
		test_call_labels_list = []
		test_call_index_dict = {}
		test_call_index_dict_cnt = 0
		# also, we will put syscalls in different sets
		test_syscall_set = set()
		new_syscall_set = set()
		# collect all syscalls from test samples
		stmt = "SELECT Testcase, CallName, CallArgs, CallRet, Level, PIPE, \
			Arg1, Arg2, Arg3, Comment FROM exit_behavior WHERE \
			Support == Total and not Testcase == 'sample_0'"
		cursor = test_conn.execute(stmt)
		for row in cursor:
			testcase = row[0]
			if testcase == 'sample_0':
				continue
			call_sign = get_sign(list(row[1:]))
			test_syscall_set.add(call_sign)
			# indexing new syscall
			if not test_call_index_dict.has_key(call_sign):
				test_call_labels_list.append([0 for x in range(test_number)])
				test_call_index_dict[call_sign] = test_call_index_dict_cnt
				test_call_index_dict_cnt += 1
			index = test_call_index_dict[call_sign]
			testcase_id = int(testcase.split('_')[-1]) - 1
			# mark the label as 1, if the syscall appears in this sample
			test_call_labels_list[index][testcase_id] = 1

		for i in test_syscall_set:
			print 'test_syscall_before:',i

		test_syscall_set -= general_syscall_set
		new_syscall_set = test_syscall_set - specific_syscall_set
		test_syscall_set -= new_syscall_set

		for i in test_syscall_set:
			print 'test_syscall_after:',i
		for i in specific_syscall_set:
			print 'specific_syscall:',i
		for i in new_syscall_set:
			print 'new_syscall:',i

		# encode categorical feature to numeric feature to make sklearn happy
		# we merge training and test feature to make sure the same encode
		X = train_X + test_X
		# we have to encode for each simple project
		if 'httpd' in env_file:
			# split the features to numeric ones and categorical ones
			numeric_X = [x[1:5]+x[7:11] for x in X]
			for i in range(len(numeric_X)):
				if numeric_X[i][3] == 'no':
					numeric_X[i][3] = '0'
			categorical_X = [[x[0],x[5],x[6]] for x in X]
			# encode categorical features
			enc = OneHotEncoder()
			enc.fit(categorical_X)
			encode_X = list(enc.transform(categorical_X).toarray())
			for i in range(len(encode_X)):
				encode_X[i] = list(encode_X[i])
			# merge numeric features and encoded categorical ones
			X = [numeric_X[i] + encode_X[i] for i in range(len(encode_X))]
			# update feature names
			feature_names = feature_names[1:5]+feature_names[7:11]
			feature_names += list(enc.get_feature_names())
			feature_names = [x.encode("utf-8") for x in feature_names]
		if 'mysql' in env_file:
			# split the features to numeric ones and categorical ones
			numeric_X = [x[15:26]+x[28:] for x in X]
			categorical_X = [x[:15]+x[26:28] for x in X]
			# encode categorical features
			enc = OneHotEncoder()
			enc.fit(categorical_X)
			encode_X = list(enc.transform(categorical_X).toarray())
			for i in range(len(encode_X)):
				encode_X[i] = list(encode_X[i])
			# merge numeric features and encoded categorical ones
			X = [numeric_X[i] + encode_X[i] for i in range(len(encode_X))]
			# update feature names
			feature_names = feature_names[15:26]+feature_names[28:]
			feature_names += list(enc.get_feature_names())
			feature_names = [x.encode("utf-8") for x in feature_names]
		if 'chrome' in env_file:
			# split the features to numeric ones and categorical ones
			numeric_X = [[x[0],x[12]] for x in X]
			categorical_X = [x[1:12]+x[13:] for x in X]
			# encode categorical features
			enc = OneHotEncoder()
			enc.fit(categorical_X)
			encode_X = list(enc.transform(categorical_X).toarray())
			for i in range(len(encode_X)):
				encode_X[i] = list(encode_X[i])
			# merge numeric features and encoded categorical ones
			X = [numeric_X[i] + encode_X[i] for i in range(len(encode_X))]
			# update feature names
			feature_names = feature_names[0:1]+feature_names[12:13]
			feature_names += list(enc.get_feature_names())
			feature_names = [x.encode("utf-8") for x in feature_names]
		if 'thunder' in env_file:
			# split the features to numeric ones and categorical ones
			categorical_X = X
			# encode categorical features
			enc = OneHotEncoder()
			enc.fit(categorical_X)
			encode_X = list(enc.transform(categorical_X).toarray())
			for i in range(len(encode_X)):
				encode_X[i] = list(encode_X[i])
			# merge numeric features and encoded categorical ones
			X = [encode_X[i] for i in range(len(encode_X))]
			# update feature names
			feature_names = list(enc.get_feature_names())
			feature_names = [x.encode("utf-8") for x in feature_names]
		if 'smplayer' in env_file:
			# split the features to numeric ones and categorical ones
			numeric_X = [x[34:38] for x in X]
			categorical_X = [x[:34] for x in X]
			# encode categorical features
			enc = OneHotEncoder()
			enc.fit(categorical_X)
			encode_X = list(enc.transform(categorical_X).toarray())
			for i in range(len(encode_X)):
				encode_X[i] = list(encode_X[i])
			# merge numeric features and encoded categorical ones
			X = [numeric_X[i] + encode_X[i] for i in range(len(encode_X))]
			# update feature names
			feature_names = feature_names[34:38]
			feature_names += list(enc.get_feature_names())
			feature_names = [x.encode("utf-8") for x in feature_names]

		# train decision trees
		decision_tree_list = []
		for i in range(len(labels_group_list)):
			# the first element is sample_0, we don't want it
			Y = labels_group_list[i][1:]
			clf = tree.DecisionTreeClassifier()
			#print X[:-test_number]
			#print
			#print Y
			clf = clf.fit(X[:-test_number],Y)
			decision_tree_list.append(clf)

			# visualize decision trees, save the tress as pictures
			'''
			dot_data = tree.export_graphviz(clf, feature_names=feature_names,
                                out_file=None, filled=True, rounded=True)
			graph = pydotplus.graph_from_dot_data(dot_data)
			colors = ('turquoise', 'orange')
			edges = collections.defaultdict(list)
			for edge in graph.get_edge_list():
			    edges[edge.get_source()].append(int(edge.get_destination()))
			for edge in edges:
			    edges[edge].sort()    
			    for j in range(2):
			        dest = graph.get_node(str(edges[edge][j]))[0]
			        dest.set_fillcolor(colors[j])
			graph.write_png('tree_%d.png'%i)
			'''

		# evaluate
		precision_list = []
		recall_list = []
		# for each syscall in test samples
		for test_syscall in sorted(test_syscall_set):
			# get true labels of the syscall
			index = test_call_index_dict[test_syscall]
			true_Y = test_call_labels_list[index]
			# get pred labels of the syscall
			group_index = call_labelsgroup_dict[test_syscall]
			pred_Y = decision_tree_list[group_index].predict(X[-test_number:])
			pred_Y = list(pred_Y)
			#print '%.2lf'%precision_score(true_Y, pred_Y),
			#print '%.2lf'%recall_score(true_Y, pred_Y)
			precision_list.append(float(precision_score(true_Y, pred_Y)))
			recall_list.append(float(recall_score(true_Y, pred_Y)))

		# for syscalls that never happen in training samples
		# we predict them will not happen: 100% precision and 0% recall
		for test_syscall in sorted(new_syscall_set):
			precision_list.append(float(0.0))
			recall_list.append(float(0.0))

		# print result
		print len(precision_list)
		print len(test_syscall_set)
		#print precision_list
		for i in range(len(test_syscall_set)):
			print '%.2f'%precision_list[i],'%.2f'%recall_list[i],
			print sorted(test_syscall_set)[i]
		print '%.2f'%statistics.mean(precision_list),
		print '%.2f'%statistics.stdev(precision_list)
		print '%.2f'%statistics.mean(recall_list),
		print '%.2f'%statistics.stdev(recall_list)
		p = statistics.mean(precision_list)
		r = statistics.mean(recall_list)
		print '%.2f'%(100 * (2*p*r)/(p+r))


# if in predicting step
if __name__ == "__main__":

	# for training samples
	global conn
	global env_file

	# for test samples
	global test_conn
	global test_env_file

	# parse command line options
	database_dir = './results.httpd-2/traces.db'
	env_file = './env/httpd-env/httpd-4-2.env'
	test_database_dir = './results.httpd-0/traces.db'
	test_env_file = './env/httpd-env/httpd-test.env'

	opts, args = getopt.getopt(sys.argv[1:], 'd:e:h')
	for op, value in opts:
		if op == '-d':
			database_dir = value
		if op == '-e':
			env_file = value
		if op == '-t':
			test_database_dir = value
		if op == '-f':
			test_env_file = value
		if op == '-h':
			usage()
			sys.exit(0)

	conn = connect(database_dir)
	test_conn = connect(test_database_dir)
	conn.text_factory = str
	test_conn.text_factory = str
	do_predicting()
	conn.commit()
	test_conn.commit()
	conn.close()
	test_conn.close()
