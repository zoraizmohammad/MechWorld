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

## Run multiple copies of the script, one for each isotropy level [0.33, 0.72, 1.00]
#$ -t 1-75:1

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

# Select isotropy based on task id using an array
# Divide tasks evenly across the specified params, ex 30 tasks / 3 params = 10 networks of each isotropy
params=(0.60 0.62 0.64 0.66 0.68)
params_length=${#params[@]}
c_density_parameter=${params[$SGE_TASK_ID % $params_length]}

echo "Running Task ${SGE_TASK_ID} with parameter: ${c_density_parameter}"

python src/task_create_and_process_network.py 300 ${c_density_parameter} 0.75 results/FS-093/ ${JOB_ID} ${SGE_TASK_ID} --dist "FS=2=100=0.93" --write_dumps

# echo job info on joblog:
echo "Job $JOB_ID ended on:   " `hostname -s`
echo "Job $JOB_ID ended on:   " `date `
echo " "
#### submit_job.sh STOP ####