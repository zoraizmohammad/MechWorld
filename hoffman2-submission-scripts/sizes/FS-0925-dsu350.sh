#### submit_job.sh START ####
#!/bin/bash
#$ -cwd
# error = Merged with joblog
#$ -o joblog.$JOB_ID
#$ -j y

## Resource Allocation...
## When testing with qrsh, this sequence worked with one core and 3G of memory
#$ -l h_rt=6:00:00,h_data=8G
#$ -pe shared 8

## Notify this Email Address...
#$ -M jrrm@g.ucla.edu

## Notify When...
#$ -m bea

## Number of networks to create and run in parallel
#$ -t 1-5:1

# echo job info on joblog:
echo "Job $JOB_ID started on:   " `hostname -s`
echo "Job $JOB_ID started on:   " `date `
echo " "

# Load job environment... (python & intel libs)
. /u/local/Modules/default/init/modules.sh
module load python
module load intel

cd /u/home/j/jrrm/Eldredge-PG-Sim
echo "Loading venv from $(pwd)..."
source .venv/bin/activate

echo "Running Task ${SGE_TASK_ID} with parameter: ${c_isotropic_parameter}"

python src/task_create_and_process_network.py 350 0.7 0.72 results/flory-schulz-0925-sizes/ ${JOB_ID} ${SGE_TASK_ID} --dist "FS-2-100-0.925"

# echo job info on joblog:
echo "Job $JOB_ID ended on:   " `hostname -s`
echo "Job $JOB_ID ended on:   " `date `
echo " "
#### submit_job.sh STOP ####