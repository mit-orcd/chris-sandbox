#!/bin/bash

#
# Bash script to round robin one core from the list available to an srun stage, based on the SLURM_LOCALID variable
# The selectd core can then be used a taskset bind target for subsequent process pinning
#

# Get the list of CPUs as a bit string and then convert to an array of cpu decimal rank numbers
cpu_bit_string=`taskset -p $$ | awk '{print $6}' | awk '{print "obase=2\nibase=16\n"toupper($1)}'  | bc`
cpu_list=( `echo ${cpu_bit_string} | awk '{ split($0, chars, ""); for (i=1; i <= length($0); i++) { if( chars[i] == '1'){printf("%d ", i-1)} };print "\n" }'` )

# Chose an entry form the array of rank numbers based on SLURM_LOCALID value as an index (modulo length of array of rank numbers).
core_num=`echo ${SLURM_LOCALID} ${#cpu_list[*]} | awk '{print $1%$2}'`
mycore=${cpu_list[${core_num}]}

# Print out which core(s) was(were) chosen for this SLURM_LOCALID
echo "OK "`hostname`" you should use CPU core(s) "${mycore}" with the \"${SLURM_LOCALID}\" srun instance on this node."
