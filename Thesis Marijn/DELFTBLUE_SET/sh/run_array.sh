#!/bin/bash
#SBATCH --job-name=KM_array
#SBATCH --account=Education-TPM-MSc-CoSEM
#SBATCH --partition=compute-p1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=47
#SBATCH --mem-per-cpu=3968M
#SBATCH --time=12:00:00
#SBATCH --array=1-27%1

cd "$HOME/Thesis Marijn/DELFTBLUE_SET" || exit 1

module purge
module load 2024r1
module unload compiler-2024
module load gcc/12.3.0 gurobi/12.0.0 miniconda3

source /apps/generic/miniconda3/4.12.0/etc/profile.d/conda.sh
conda activate calliope

SCENARIO_FILE="$HOME/Thesis Marijn/DELFTBLUE_SET/scenario_list.txt"
SCENARIO=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$SCENARIO_FILE")

if [ -z "$SCENARIO" ]; then
    echo "No scenario found for SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID}"
    exit 1
fi

echo "Running array task ${SLURM_ARRAY_TASK_ID}: $SCENARIO"
python "$HOME/Thesis Marijn/DELFTBLUE_SET/Runfile_BL_generic.py" "$SCENARIO"