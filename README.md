SafeExit
---

###Automatically Detecting Missing Cleanup for Ungraceful Exits


Software encounters ungraceful exits due to either bugs in the interrupt/signal handler code or the intention of developers to debug the software. Users may su er from "weird" problems caused by leftovers of the ungraceful exits. A common practice to fix these problems is rebooting, which wipes away the stale state of the software. This solution, however, is heavyweight and often leads to poor user experience because it requires restarting other normal processes. 

SafeExit is a tool that can automatically detect and pinpoint the root causes of the problems caused by ungraceful exits, which can help users fix the problems using lightweight solutions. Specifically, SafeExit checks the program exit behaviors in the case of an interrupted execution against its expected exit behaviors to detect the missing cleanup behaviors required for avoiding the ungraceful exit. The expected behaviors are obtained by monitoring the program exit under a normal execution. 


###Usage
Clone SafeExit source code, and change the directory to SafeExit:

```
git clone https://github.com/ZhouyangJia/SafeExit.git
cd SafeExit
```

---

Step 0: Install the target program (taking nginx as an example), and prepare the config file:

```
# config file example
cat conf/nginx.ini
```

---

Step 1: Test the target program under one normal execution and 13 signal(abnormal) executions (it may take minutes):

```
./script/run.sh test nginx
```
This step will output a directory named results.nginx, including the system calls invoded by the target program.

---

Step 2: Clean the raw data:

```
./script/run.sh clean nginx
```
This step will generate a SQlite3 database file named traces.db.

---

Step 3: Extract system calls of the exit stage:

```
./script/run.sh extract nginx
```
This step will generate a table named 'exit\_traces'.

---

Step 4: Mine exit behaviors of the normal execution.

```
./script/run.sh mine nginx
./script/run.sh cluster nginx
```
This step will generate tables named 'exit\_behavior' and 'exit\_cluster'. A behavior is a system call, while a cluster is a sequence of system calls.

---

Step 5: Hunt missing behaviors of signal(abnormal) executions:

```
./script/run.sh hunt nginx
```
This step will generate tables named 'miss\_behavior' and 'miss\_cluster'. 

---

Please note:

* You can use the following commands for all above steps:

```
./script/run.sh all nginx
```

* The second argument of the script 'run.sh' should be the same to the name of config file.

* The current time interval between start and stop of the target program is 5 seconds. Some programs may require longer execution time, you may need to change the time interval in 'run.sh'.

* The directory 'data/' includes data in the paper:

Zhouyang Jia, Shanshan Li, Tingting Yu, Xiangke Liao, and Ji Wang. 2019. Automatically detecting missing cleanup for ungraceful exits. In Proceedings of the 2019 27th ACM Joint Meeting on European Software Engineering Conference and Symposium on the Foundations of Software Engineering (ESEC/FSE 2019). ACM, New York, NY, USA, 751-762. DOI: https://doi.org/10.1145/3338906.3338938

###Have fun