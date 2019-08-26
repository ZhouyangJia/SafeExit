import os
import sys
import getopt
import mining
import subprocess
import pygraphviz as pgv
from sqlite3 import connect


# usage of this script
def usage():
	print '%s: locate missing behaviors in source code'%sys.argv[0]
	print 'Usage:'
	print '\tpython %s [-t <traces_dir>] [-d <database_dir>]'%sys.argv[0]
	print '\tpython %s [-h]'%sys.argv[0]
	print 'Options:'
	print '\t-t specify the path to the traces directory'
	print '\t-d specify the path of database'
	print '\t-h print help messages'


# name demangling for c++
def demangle(name):
    args = ['c++filt']
    args.append(name)
    pipe = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    demangled = pipe.communicate()[0].strip()
    return demangled


# get location of a given call-stack line
def get_location(trace_line):

	[binary_file, binary_addr] = trace_line[2:trace_line.rfind(')')].split('(')
	[function_name, call_offset] = binary_addr.split('+')
	call_offset = int(call_offset, 16)
	#print binary_file, function_name, call_offset

	proc = subprocess.Popen('nm %s 2> /dev/null | grep %s' % (binary_file, function_name), shell=True,
							stdout=subprocess.PIPE)
	proc_res = proc.communicate()[0].split(' ')[0]
	#print hex(proc_res)

	try:
		function_offset = int(proc_res, 16)
		call_offset = int(proc_res, 16) + call_offset - 1
	except Exception:
		function_offset = 0
		call_offset = 0
	#print hex(call_offset)

	proc = subprocess.Popen('addr2line -e %s %s' % (binary_file, hex(function_offset)), shell=True,
							stdout=subprocess.PIPE)
	function_location = proc.communicate()[0].strip()
	proc = subprocess.Popen('addr2line -e %s %s' % (binary_file, hex(call_offset)), shell=True,
							stdout=subprocess.PIPE)
	call_location = proc.communicate()[0].strip()
	#print location

	return [function_name, function_location, call_location]

def do_locating():

	miss_behavior = []
	stmt = "SELECT * from miss_behavior"
	cursor = conn.execute(stmt)
	for row in cursor:
		miss_behavior.append(list(row))

	node_dict = {}
	node_cnt = 1
	edge_list = []
	father_node_dict = {}

	# collect behaviors from exit_behavior
	stmt = "SELECT ID, PID, ExecTime, CallName, PIPE FROM exit_behavior"
	cursor = conn.execute(stmt)
	for row in cursor:
		[behavior_id, pid_num, exec_time, call_name, pipe] = row
		print [behavior_id, pid_num, exec_time, call_name, pipe]
		node_str = str(behavior_id) + '_' + call_name + '_' + pipe
		if not node_dict.has_key(node_str):
			node_dict[node_str] = '('+str(node_cnt)+')'+node_str
			node_cnt += 1

		# find trace file
		proc = subprocess.Popen('find %s | grep %s' % (traces_dir, pid_num), shell=True,
				stdout=subprocess.PIPE)
		proc_res = proc.communicate()[0].split(' ')[0]
		proc_res = proc_res.strip()

		# get file content
		trace_file = open(proc_res, 'r')
		lines = trace_file.readlines()
		lines = [x.strip() for x in lines]
		#print len(lines)
		trace_file.close()

		# search line num
		trace_file = open(proc_res, 'r')
		line_num = 0
		for num, line in enumerate(trace_file, 1):
			if exec_time in line:
				line_num = num
				break
		if line_num == 0:
			continue

		last_node_str = node_str
		tmp_edge_list = []
		while line_num < len(lines) and '> ' in lines[line_num]:
			[function_name, function_location, call_location] = get_location(lines[line_num])

			if '?' not in function_location and '?' not in call_location:
				print lines[line_num]
				print [function_name, function_location, call_location]
				node_str = str([function_name, function_location, call_location])

				if not node_dict.has_key(node_str):
					call_line = call_location[call_location.find(':')+1:]
					if ' (discriminator' in call_line:
						call_line = call_line[:call_line.find(' (discriminator')]
					node_dict[node_str] = '('+str(node_cnt)+')'+function_name+':'+call_line
					node_cnt += 1

				tmp_edge_list.append((node_dict[node_str], node_dict[last_node_str]))
				last_node_str = node_str
			line_num += 1

		
		is_changed = True
		lenth = len(tmp_edge_list)
		while is_changed and lenth > 2:
			is_changed = False
			for i in range(1, len(tmp_edge_list)):
				n1, n2 = tmp_edge_list[i]
				if not father_node_dict.has_key(n2):
					father_node_dict[n2] = n1
				else:
					if father_node_dict[n2] != n1:
						m1, m2 = tmp_edge_list[i - 1]
						new_edge = (n1, m2)
						tmp_edge_list = tmp_edge_list[:i-1] + [new_edge] + tmp_edge_list[i+1:]
						is_changed = True
						break
		

		edge_list.extend(tmp_edge_list)
		trace_file.close()

	#for item, key in node_dict.items():
	#	print item, key
	edge_list = list(set(edge_list))
	#for n1, n2 in edge_list:
	#	print n1, n2

	node_list = []
	red_node = []
	G=pgv.AGraph(strict=False,directed=True)
	for n1, n2 in edge_list:
		G.add_edge(n1, n2)
		node_list.append(n1)
		node_list.append(n2)

	# red leaf
	for node in node_list:
		if '[' in node:
			n=G.get_node(node)
			n.attr['shape']='box'
			behavior_id = node[node.find(')')+1 : node.find('_')]
			for item in miss_behavior:
				if str(item[3]) == behavior_id:
					if item[15] == 0:
						n.attr['color']='red'
						red_node.append(node)

	# red all
	is_changed = True
	while is_changed:
		is_changed = False
		for node in node_list:
			if node in red_node:
				continue

			has_child = False
			all_red_children = True
			for n1, n2 in edge_list:
				if n1 == node:
					has_child = True
					if n2 not in red_node:
						all_red_children = False
						break
			if has_child == True and all_red_children == True:
				n=G.get_node(node)
				n.attr['color']='red'
				red_node.append(node)
				is_changed = True


	G.layout(prog='dot')
	G.write("file.dot")
	G.draw('file.png')


# if in hunting step
if __name__ == "__main__":

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
	do_locating()
	conn.commit()
	conn.close()
