#!/bin/bash

# config file
FILE_CONF="conf/${2}.ini"

# data directory
DIR_RESULT="results.${2}"

# trace direcotry
DIR_TRACE="${DIR_RESULT}/traces"

# trace database
FILE_DB="${DIR_RESULT}/traces.db"

# testing
do_testing(){
	sudo ls > /dev/null
	time sudo python src/testing.py -c ${FILE_CONF} -t ${DIR_TRACE} -s 5 -m normal -e 1
	time sudo python src/testing.py -c ${FILE_CONF} -t ${DIR_TRACE} -s 5 -m signal -e 1
}

# cleaning
do_cleaning(){
	time python src/cleaning.py -t ${DIR_TRACE} -d ${FILE_DB}
}

# extracting
do_extracting(){
	time python src/extracting.py -d ${FILE_DB}
}

# mining
do_mining(){
	time python src/mining.py -d ${FILE_DB}
}

# clustering
do_clustering(){
	time python src/clustering.py -d ${FILE_DB}
}

# hunting
do_hunting(){
	time python src/hunting.py -d ${FILE_DB}
}

# all steps
do_all(){
	do_testing
	do_cleaning
	do_extracting
	do_mining
	do_clustering
	do_hunting
}

case "$1" in
	"test")
		do_testing
		;;
	"clean")
		do_cleaning
		;;
	"extract")
		do_extracting
		;;
	"mine")
		do_mining
		;;
	"cluster")
		do_clustering
		;;
	"hunt")
		do_hunting
		;;
	"all")
		do_all
		;;
	*)
		>&2 echo "Bad arguments!"
		>&2 echo "Usage: $0 {all|test|clean|extract|mine|cluster|hunt}"
		>&2 echo "    all      Run all steps"
		>&2 echo "    test     Run testing step only"
		>&2 echo "    clean    Run cleaning step only"
		>&2 echo "    extract  Run extracting step only"
		>&2 echo "    mine     Run mining step only"
		>&2 echo "    cluster  Run clustering step only"
		>&2 echo "    hunt     Run hunting step only"
		;;
esac
