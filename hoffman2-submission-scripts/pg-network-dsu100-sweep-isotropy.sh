#### submit_job.sh START ####
#!/bin/bash
#$ -cwd
# error = Merged with joblog
#$ -o joblog.$JOB_ID
#$ -j y

## Resource Allocation...
#$ -l h_rt=1:00:00,h_data=2G
#$ -pe shared 8

## Notify this Email Address...
#$ -M jrrm@g.ucla.edu

## Notify When...
#$ -m bea

## Run multiple copies of the script, one for each isotropy level [0.33, 0.72, 1.00]
#$ -t 1-3:1

# echo job info on joblog:
echo "Job $JOB_ID started on:   " `hostname -s`
echo "Job $JOB_ID started on:   " `date `
echo " "

# Load job environment...
. /u/local/Modules/default/init/modules.sh
module load python

cd ~/Eldredge-PG-Sim
echo "Loading venv from $(pwd)..."
source .venv/bin/activate

## Select isotropy based on task id using an array
params=(0 0.33 0.72 1.00) # 0 is dummy with idx 0
c_isotropic_parameter=${params[$SGE_TASK_ID]}

echo "Running Task ${SGE_TASK_ID} with parameter: ${c_isotropic_parameter}"

python src/create_and_process_single_network.py 100 1.0 ${c_isotropic_parameter} results/

# echo job info on joblog:
echo "Job $JOB_ID ended on:   " `hostname -s`
echo "Job $JOB_ID ended on:   " `date `
echo " "
#### submit_job.sh STOP ####