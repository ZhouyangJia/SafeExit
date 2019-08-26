import os
import sys
import getopt
import subprocess


def demangle(name):
    args = ['c++filt']
    args.append(name)
    pipe = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    demangled = pipe.communicate()[0].strip()
    return demangled


trace_file_name = ''
opts, args = getopt.getopt(sys.argv[1:], 't:h')
for op, value in opts:
	if op == '-t':
		trace_file_name = value
	if op == '-h':
		sys.exit(0)

trace_file = open(trace_file_name, 'r')
trace_lines = trace_file.readlines()
trace_file.close()

output_file_name = trace_file_name + '.location'
output_file = open(output_file_name, 'w')

for trace_line in trace_lines:
	trace_line = trace_line.strip()

	if '> ' not in trace_line:
		output_file.write('\n%s\n'%trace_line)
		continue

	[binary_file, call_addr] = trace_line[2:trace_line.rfind(')')].split('(')
	[call_name, call_offset] = call_addr.split('+')
	call_offset = int(call_offset, 16)

	proc = subprocess.Popen('nm %s | grep %s' % (binary_file, call_name), shell=True,
							stdout=subprocess.PIPE)
	proc_res = proc.communicate()[0].split(' ')[0]

	try:
		binary_offset = int(proc_res, 16) + call_offset - 1
	except Exception:
		binary_offset = 0

	proc = subprocess.Popen('addr2line -e %s %s' % (binary_file, hex(binary_offset)), shell=True,
							stdout=subprocess.PIPE)
	location = proc.communicate()[0].strip()
	res = location+' # '+demangle(call_name)+'@'+binary_file
	output_file.write('%s\n'%res)
	output_file.flush()

output_file.close()
