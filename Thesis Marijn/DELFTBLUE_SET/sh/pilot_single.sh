#!/bin/bash
#SBATCH --job-name=KM_pilot
#SBATCH --account=Education-TPM-MSc-CoSEM
#SBATCH --partition=compute-p1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=3968M
#SBATCH --time=08:00:00

cd "$HOME/Thesis Marijn/DELFTBLUE_SET" || exit 1

module purge
module load 2024r1
module unload compiler-2024
module load gcc/12.3.0 gurobi/12.0.0 miniconda3

source /apps/generic/miniconda3/4.12.0/etc/profile.d/conda.sh
conda activate calliope

SCENARIO="base_run_KM_W3_L3_P3"

echo "Running pilot scenario: $SCENARIO"
python "$HOME/Thesis Marijn/DELFTBLUE_SET/Runfile_BL_generic.py" "$SCENARIO"