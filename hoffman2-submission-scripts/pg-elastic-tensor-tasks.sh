#### submit_job.sh START ####
#!/bin/bash
#$ -cwd
# error = Merged with joblog
#$ -o joblog.$JOB_ID
#$ -j y

## Resource Allocation...
## When testing with qrsh, this sequence worked with one core and 3G of memory
#$ -l h_rt=1:00:00,h_data=4G
#$ -pe shared 8

## Notify this Email Address...
#$ -M jrrm@g.ucla.edu

## Notify When...
#$ -m bea#$ -t 1-30:1
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
task_file_arr=("C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.04.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.15.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.06.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.21.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.22.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.23.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.24.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.19.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.08.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.01.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.09.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.27.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.29.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.14.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.28.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.17.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.13.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.26.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.3.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.05.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.16.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.18.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.07.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.11.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.02.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.1.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.03.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.25.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.12.restart" "C:\Users\jrrm5\Desktop\Eldredge\PG-sims\Github\test_restarts\job1.2_dsu100_rho100_a72_prestr0.2.restart")
c_filename=${task_file_arr[$SGE_TASK_ID]}
echo "Running Task ${SGE_TASK_ID} with parameter: ${c_isotropic_parameter}"

python src/create_and_process_single_network.py ${c_filename}

# echo job info on joblog:
echo "Job $JOB_ID ended on:   " `hostname -s`
echo "Job $JOB_ID ended on:   " `date `
echo " "
#### submit_job.sh STOP ####