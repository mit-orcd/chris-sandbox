#!/bin/bash
#
#SBATCH -N 10
#SBATCH --tasks-per-node=2
#SBATCH --cpus-per-task=1
#SBATCH -m cyclic
#SBATCH -p sched_mit_orcd
#SBATCH -o foo_out_io_%N_%t.txt 
#

#
#
# Example Slurm script for running iotest over multiple nodes.
#
#

## CHANGE THIS TO YOUR DIRECTORIES
CODE_DIR=/net/fstor001/fhome/cnh/mc
WORK_DIR=/net/hstor001.ib/cnh/001


cd ${CODE_DIR}

#
# To install everything ( for example  ), if not already isntalled.
# $ curl -O https://repo.anaconda.com/miniconda/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh
# $ chmod +x Miniconda3-py310_23.11.0-2-Linux-x86_64.sh
# $ ./Miniconda3-py310_23.11.0-2-Linux-x86_64.sh -p mc3 -b
# $ . mc3/bin/activate
# $ conda create -n py312 python=3.12
# $ conda activate py312
# $ curl -O https://raw.githubusercontent.com/mit-orcd/chris-sandbox/cnh/io_check/io_tests/hstor_fstor_perfmon/requirements.txt
# $ pip install --user -r requirements.txt
# $ curl -O https://raw.githubusercontent.com/mit-orcd/chris-sandbox/cnh/io_check/io_tests/hstor_fstor_perfmon/rndfilesio.py
#

# Set up conda
source mc3/bin/activate
conda activate py312
which python

cp ./rndfilesio.py ${WORK_DIR}
cd ${WORK_DIR}
# We put run command in script just to pass ${SLURM_PROCID} cleanly to each process started by srun
cat > mycommand.sh <<EOF
#!/bin/bash
#
mycore=\`${CODE_DIR}/tscmd.sh\`
EOF

cat >> mycommand.sh <<'EOF'

# debug testing
taskset --cpu-list ${mycore} ./rndfilesio.py io_test ${SLURM_PROCID} 10 10 1000

# lots of small files
# ./rndfilesio.py  io_test ${SLURM_PROCID} 1000 1000 1000

# bigger files
# ./rndfilesio.py  io_test ${SLURM_PROCID} 10 100 5000000
EOF
chmod +x mycommand.sh

# Start test
date
/bim/rm -f foo2_out_*txt
srun -o foo2_out_io_%N_%t.txt ./mycommand.sh
date
