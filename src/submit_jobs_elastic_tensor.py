from utils_helpers import find_files
import argparse
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("directory")
args = parser.parse_args()

if args.directory:
    directory = str(args.directory);

files_to_process = find_files(directory, r".+_prestr\d\.\d+\.restart");

ntasks = len(files_to_process);

# we are going to write a job submission file, using one task per file

project_root = os.path.join(os.path.dirname(__file__),"..");
submission_script_filepath = os.path.join(project_root,"hoffman2-submission-scripts","pg-elastic-tensor-tasks.sh");

with open(submission_script_filepath,"w") as f:
    f.write("""#### submit_job.sh START ####
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
#$ -m bea""");
    
    if (ntasks > 1):
        f.write(f"#$ -t 1-{ntasks}:1\n");

    f.write("""# echo job info on joblog:
echo \"Job $JOB_ID started on:   \" `hostname -s`
echo \"Job $JOB_ID started on:   \" `date `
echo \" \"

# Load job environment... (python & intel libs)
. /u/local/Modules/default/init/modules.sh
module load python
module load intel

cd /u/home/j/jrrm/Eldredge-PG-Sim
echo \"Loading venv from $(pwd)...\"
source .venv/bin/activate\n""");
    
    if (ntasks > 1):
        task_file_arr = "task_file_arr=(";
        for filepath in files_to_process:
            task_file_arr += "\"" + filepath + "\" ";
        task_file_arr = task_file_arr[0:-1]+')\n';

        f.write(task_file_arr)
        f.write("c_filename=${task_file_arr[$SGE_TASK_ID]}\n")
    else:
        f.write(f"c_filename=\"{files_to_process.pop()}\"\n")

    f.write("""echo \"Running Task ${SGE_TASK_ID} with parameter: ${c_isotropic_parameter}\"

python src/create_and_process_single_network.py ${c_filename}

# echo job info on joblog:
echo \"Job $JOB_ID ended on:   \" `hostname -s`
echo \"Job $JOB_ID ended on:   \" `date `
echo \" \"
#### submit_job.sh STOP ####""");

# use cmd to run job submission script
subprocess.run(["qsub",os.path.join("hoffman2-submission-scripts","pg-network-dsu100-sweep-isotropy.sh")])