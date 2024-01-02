#!/usr/bin/env python


import numpy as np
import os
import sys
import time
import datetime
import socket
import platform
import multiprocessing
import psutil

#
# requirements.txt
# (
#  numpy==1.26.2
#  psutil==5.9.7
#  termplotlib==0.3.9
# )
#

#
# Small I/O testing Python code. 
#
# o Writes a user specified number of files to each directory of a user spcified number of directories. 
# o The files are all of the same size that is also user specified.
# o File contents are created using random number generator.
# o A "rank" argument sets a parent directory for each set of otputs, to support multiple instances
#   running concurrently.
# o Each rank can use the same random number generator seed, so that file dedup can be tested.
# o A testid argument sets a top-level directory that holds all the test generated files.

# Example run command
#
# ./genrndfile.py test001 0 10 10 1024 
#
# This will produce a series of directories

#  test001/rank_0/d_000000/
#    :
#  test001/rank_0/d_000009/
#
# with each directory containing files 
#
#  foo0.out ... foo9.out
#
# where each foo0.out is 1024 random bytes.
# 
# The program times the I/O sections of its exectution and produces statistics and plots
# of performance.
# For automated monitoring the "Elapsed I/O time:" output for a standard amount of work is 
# a simple check. It can be compared against a reference value to look for anomalous 
# performance.
#
# Two flags in the code can be used to change behavior
#  1. dedup_testing=True
#     The default setting ( True ) uses the same seed for every directory. This means that each directory
#     will have files with the same content written. This can test dedup capabilities for cases where
#     the file data varies.
#
#  2. vary_file_content=False
#     The default setting ( False ) means that every file will have the same content. This can be used
#     to test dedup where every file in every directory has the same content.
#
# the default settings has the fastest runtimes as they ony generate random data to use once. Generating
# random data requires a non-negligible amut of CPU time.
#
# The timing statistics reported in "Elapsed I/O time:" are timing of elapsed time for the I/O stages only.
#
#

def bytes2human(n):
    # http://code.activestate.com/recipes/578019
    # >>> bytes2human(10000)
    # '9.8K'
    # >>> bytes2human(100001221)
    # '95.4M'
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if abs(n) >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n


# Get command lin arguments
#  - testid, rank, number of directories, files per directory, bytes per file
na=len(sys.argv)
if na == 1:
    # No command line arguments so use some defaults.
    TESTID="io_test"
    MYRANK="0"
    ND=10
    NF=10
    NB=1024
elif na != 6:
    # Wrong number, print usage.
    print("Usage: %s [TESTID MYRANK ND NF NB]"%(sys.argv[0]))
    exit(-1)
else:
    TESTID=sys.argv[1]
    MYRANK=sys.argv[2]
    ND=int(sys.argv[3])
    NF=int(sys.argv[4])
    NB=int(sys.argv[5])

DROOT="%s/rank_%s"%(TESTID,MYRANK)
nd=ND
nf=NF
nbytes=NB
dedup_testing=True
vary_file_content=False
if vary_file_content:
    dedup_testing=True


# Write some summary
print("#R_%s Start time: %s"%(MYRANK,(datetime.datetime.now()).__str__() ))

print("#R_%s ******* SETUP *********"%(MYRANK))
print("#R_%s Running on: %s"%(MYRANK, socket.gethostbyaddr(socket.gethostname())[0]) )
print("#R_%s Running with OS: %s"%(MYRANK, platform.uname() ) )
print("#R_%s Available CPU cores: %d"%(MYRANK, multiprocessing.cpu_count() ) )
p=psutil.Process()
print("#R_%s CPU affinity: "%(MYRANK), p.cpu_affinity()  )
print("#R_%s Running in directory: %s"%(MYRANK, os.getcwd() ) )
print("#R_%s Writing to directory: %s/%s"%(MYRANK, os.getcwd(),DROOT ) )
print("#R_%s Number of directories requested: %d"%(MYRANK,nd))
print("#R_%s Number of files requested: %d"%(MYRANK,nd*nf))
print("#R_%s Number of bytes per file: %d, %s"%(MYRANK,nbytes,bytes2human(nbytes)))
print("#R_%s Total number of bytes requested: %d, %s"%( MYRANK,nd*nf*nbytes,bytes2human(nd*nf*nbytes)))
print("#R_%s Duplicate files requested: "%(MYRANK),dedup_testing)
print(" ")

# exit()

# Create initial random data generator
rng = np.random.default_rng(12345)

# Create requested directory tree
for dnum in range(nd):
    os.makedirs("%s/d_%6.6d"%(DROOT,dnum),exist_ok=True)


# Set up some timers/counters
dt0=datetime.datetime.now()
pt0=time.process_time()
bytes_written=np.int64(0)
files_written=np.int64(0)
iotime_sum=np.float64(0.)
iotime_max=np.float64(0.)
iotime_min=np.float64(1.e12)
iotime2_sum=np.float64(0.)
proc_iotime=np.float64(0.)

# For histogram
io_time_arr=np.zeros(nd*nf)

# Fixed random numbers, for doing identical to every file.
rng = np.random.default_rng(12345)
phi_fixed=rng.integers(low=-np.array([2**63-1]),high=np.array([2**63-1]),size=int(nbytes/8))
phi=phi_fixed

# Do some I/O
for dnum in range(nd):
    if dedup_testing:
        # Reinitialize generator with same seed for each directory - for dedup testing
        rng = np.random.default_rng(12345)
    for fnum in range(nf):
        # Generate random data on the fly
        if vary_file_content:
             phi=rng.integers(low=-np.array([2**63-1]),high=np.array([2**63-1]),size=int(nbytes/8))
        fout="%s/d_%6.6d/foo%d.out"%(DROOT,dnum,fnum)

        # Timed I/O begins here (probably should use _ns for small I/O )
        dt00=datetime.datetime.now()
        pt00=time.process_time()

        phi.tofile(fout)

        pt01=time.process_time()
        dt01=datetime.datetime.now()
        # Timed I/O ends here
     
        # Accumulate I/O time statistics
        iotime_sum=iotime_sum+(dt01-dt00).total_seconds()
        iotime2_sum=iotime2_sum+((dt01-dt00).total_seconds())**2
        iotime_max=np.max([(dt01-dt00).total_seconds(),iotime_max])
        iotime_min=np.min([(dt01-dt00).total_seconds(),iotime_min])
        proc_iotime=proc_iotime+(pt01-pt00)
        bytes_written+=len(phi)*8
        io_time_arr[files_written]=(dt01-dt00).total_seconds()
        files_written+=1

pt1=time.process_time()
dt1=datetime.datetime.now()

# Print some statistics

print("#R_%s Process time: %f secs"%(MYRANK,pt1-pt0))
print("#R_%s Process I/O time: %f secs"%(MYRANK,proc_iotime))
elapsed_time=(dt1-dt0).total_seconds()
print("#R_%s Elapsed time: %f secs"%(MYRANK, elapsed_time ) )

elapsed_io_time=iotime_sum
print("#R_%s Elapsed I/O time: %f secs"%(MYRANK, elapsed_io_time ) )
print("#R_%s Mean overall bytes per sec: %f, %fKiB/sec %fMiB/sec %fGiB/sec"%(MYRANK, bytes_written/elapsed_io_time, 
                                          bytes_written/elapsed_io_time/1024.,
                                          bytes_written/elapsed_io_time/1024./1024.,
                                          bytes_written/elapsed_io_time/1024./1024./1024.,
                                        ) 
     )
print("#R_%s Mean overall files processed per sec: %f/sec"%(MYRANK, files_written/elapsed_io_time) )
print("#R_%s Mean overall I/O time per file: %f"%(MYRANK, elapsed_io_time/files_written) )
print("#R_%s Overall I/O time per file sigma: %f"%(MYRANK, (iotime2_sum/files_written-(iotime_sum/files_written)**2)**0.5) )
elapsed_io_time=iotime_max
print("#R_%s Minimum bytes per sec for a file: %f, %fKiB/sec %fMiB/sec %fGiB/sec"%(MYRANK, nbytes/elapsed_io_time, 
                                          nbytes/elapsed_io_time/1024.,
                                          nbytes/elapsed_io_time/1024./1024.,
                                          nbytes/elapsed_io_time/1024./1024./1024.,
                                        ) 
     )
print("#R_%s Mimimum effective file processed per sec: %f/sec"%(MYRANK, 1./elapsed_io_time) )
elapsed_io_time=iotime_min
print("#R_%s Maximum bytes per sec for a file: %f, %fKiB/sec %fMiB/sec %fGiB/sec"%(MYRANK, nbytes/elapsed_io_time, 
                                          nbytes/elapsed_io_time/1024.,
                                          nbytes/elapsed_io_time/1024./1024.,
                                          nbytes/elapsed_io_time/1024./1024./1024.,
                                        ) 
     )
print("#R_%s Maximum effective file processed per sec: %f/sec"%(MYRANK, 1./elapsed_io_time) )

# Needs - $ pip install termplotlib
print("#R_%s Bytes/sec distribution plot."%(MYRANK))
import termplotlib as tpl

sample = nbytes/io_time_arr
counts, bin_edges = np.histogram(sample)

fig = tpl.figure()
# fig.hist(counts, bin_edges, orientation="horizontal", force_ascii=False)
fig.hist(counts, bin_edges, orientation="horizontal", force_ascii=True)
fig.show()
print("#R_%s Mean of per file bytes per sec: %s/sec"%(MYRANK,bytes2human(np.mean(sample))))
print("#R_%s Median of per file bytes per sec: %s/sec"%(MYRANK,bytes2human(np.median(sample))))
print("#R_%s End time: %s"%(MYRANK,(datetime.datetime.now()).__str__() ))
