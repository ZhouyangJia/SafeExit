import random

var_name = []
var_value = []

#config variable
var_name.append('c1')
var_name.append('c2')
var_name.append('c3')
var_name.append('c4')
var_name.append('c5')
var_name.append('c6')
var_name.append('c7')
var_name.append('c8')
var_name.append('c9')

var_name.append('--default-storage-engine')
var_name.append('--binlog-format')
var_name.append('--daemonize')
var_name.append('--delay-key-write')
var_name.append('--event-scheduler')
var_name.append('--myisam-recover-options')
var_name.append('--autocommit')

var_name.append('--key-buffer-size')
var_name.append('--max-allowed-packet')
var_name.append('--max-connections')
var_name.append('--wait-timeout')
var_name.append('--interactive-timeout')

#config variable value
var_value.append(['--external-locking', '--skip-external-locking'])
var_value.append(['--character-set-client-handshake', '--skip-character-set-client-handshake'])
var_value.append(['--external-locking', ''])
var_value.append(['--big-tables', ''])
var_value.append(['--flush', ''])
var_value.append(['--memlock', ''])
var_value.append(['--skip-networking', ''])
var_value.append(['--super-large-pages', ''])
var_value.append(['--symbolic-links', ''])

var_value.append(['InnoDB', 'BLACKHOLE', 'MyISAM'])
var_value.append(['ROW', 'STATEMENT', 'MIXED'])
var_value.append(['OFF', 'ON'])
var_value.append(['ON', 'OFF', 'ALL'])
var_value.append(['ON', 'OFF', 'DISABLED'])
var_value.append(['OFF', 'DEFAULT', 'BACKUP', 'FORCE', 'QUICK'])
var_value.append([0, 1])

var_value.append(range(8, 9)) #1073741823
var_value.append(range(1024, 1025)) #1073741823
var_value.append(range(1, 100000))
var_value.append(range(1, 28800))
var_value.append(range(1, 28800))

# workload variable
var_name.append('--concurrency')
var_name.append('--iterations')
var_name.append('--number-int-cols')
var_name.append('--number-char-cols')

var_name.append('--commit')
var_name.append('c10')
var_name.append('c11')
var_name.append('--detach')

# workload variable value
var_value.append(range(1,20))
var_value.append(range(1,10))
var_value.append(range(1,10))
var_value.append(range(1,10))

var_value.append(range(0,50))
var_value.append(['--compress', ''])
var_value.append(['--enable-cleartext-plugin', ''])
var_value.append(range(0,5))


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

	values[16] = random.randrange(8, 1073741823)
	values[17] = random.randrange(1024, 1073741823)

	# [--max-connections] >= [--concurrency];
	if values[18] < values[21]:
		continue

	value_str = ''
	for value in values:
		value_str += str(value)+'\t'
	print value_str.strip()
	cnt -= 1;
