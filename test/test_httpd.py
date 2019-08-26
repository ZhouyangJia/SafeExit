import random

var_name = []
var_value = []

# workload variable
var_name.append('-k')
var_name.append('-b')
var_name.append('-n')
var_name.append('-c')
var_name.append('-t')
var_name.append('-m')

# workload variable value
var_value.append(['yes', 'no'])
var_value.append(range(4096,6291457))
var_value.append(range(50001))
var_value.append(range(201))
var_value.append(range(31))
var_value.append(['get', 'head', 'put', 'post'])

#config variable
var_name.append('KeepAlive')
var_name.append('KeepAliveTimeout')
var_name.append('MaxKeepAliveRequests')
var_name.append('StartServers')
var_name.append('Timeout')

#config variable value
var_value.append(['on', 'off'])
var_value.append(range(151))
var_value.append(range(1000000))
var_value.append(range(2, 17))
var_value.append(range(60, 301))


name_str = ''
for i in range(len(var_name)):
	name = var_name[i]
	name_str += name+'\t'
print name_str.strip()

cnt = 100
while cnt:
	values = []
	for i in range(len(var_value)):
		values.append(random.choice(var_value[i]))

	# -t might not be set
	if random.choice(range(2)) == 0:
		values[4] = 'no'

	# -m != HEAD if -k = yes
	if values[0] == 'yes' and values[5] == 'head':
		continue

	# -c <= -n
	if values[3] > values[2]:
		continue

	# -n = 50k if -t != no
	if values[4] != 'no':
		values[2] = 50000

	value_str = ''
	for value in values:
		value_str += str(value)+'\t'
	print value_str.strip()
	cnt -= 1;
