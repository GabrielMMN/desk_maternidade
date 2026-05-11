# Capacity Planning for a Public Maternity Ward Using Discrete-Event Simulation (DES)


## 📋 Overview

This repository contains the source code, data, and results of a Discrete Event Simulation (DES) model developed to assess the operational capacity of the maternity ward at a public hospital located in the Belo Horizonte metropolitan area.

The project applies the DES to hospital processes to analyze the level of service provided to the public. The model has features such as:
- **Full Clinical Pathway:** A representation of the patient flow through the system, from admission and obstetric risk classification to hospital discharge.
- **Financial Analysis:** Cost and revenue analysis based on SIGTAP/DATASUS.
- **Scenario Analysis (*What-If*):** Identification and optimization of bottlenecks in labor induction, stress testing (peak demand), and resource reallocation.

The proposed model was implemented in Python using the open-source Discrete Event Simulation Kit (DESK) framework [1].

---

## 📂 Repository Structure

The project is organized to separate the input data, the simulation engine, and the outputs (plots and logs):

```text
├── input_data/              # some historical data
├── src/desk/                # DESK framework source code
├── figures_and_graphics/    # exported graphics
├── results/                 # Event logs and replication results (.csv)
├── desk_maternidade.py      # Main script (model building and execution)
├── requirements.txt         
└── README.md                # Documentation
```
---


## 🚀 How to Use

### Installation

```bash
# Clone the repository
git clone https://github.com/GabrielMMN/desk_maternidade.git
cd desk_maternidade

# Create a virtual environment
py -m venv venv

# Allow PowerShell to activate virtual environments (run once per machine)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip inside the virtual environment
py -m pip install --upgrade pip

# Install dependencies
pip install .
# or
pip install -e .

# Then test:
desk-sim -h

desk-distfit -h
```


### Running

There are three execution modes available for the model, which can be checked as follows:

```bash
desk-sim -m desk_maternidade.py --list-modes
```

```text
DESK execution modes:

  --mode single         → run a single replication
  --mode replications   → run the full simulation
  --mode visualization  → run simulation interface
```


DESK models are executed **directly from the command line**, using explicit execution modes:



### ▶️ Running a single replication

Runs **one complete replication run**, with full tracing, reporting, plots, and diagnostics.

```bash
desk-sim -m desk_maternidade.py --mode single
```

---

### 📊 Running the full simulation (multiple replications)

Runs **multiple independent replications**, aggregates results, and computes confidence intervals and statistical analysis.

```bash
desk-sim -m desk_maternidade.py --mode replications
```

---

### 🔁 Interactive visualization

Runs the model using the **DESK visualization interface**, enabling interactive inspection of the evolving system.

```bash
desk-sim -m desk_maternidade.py --mode visualization
```

---

## 🔗 About DESK

This project was developed using an adapted version of DESK, an open-source Discrete Event Simulation framework based on the SimPy library. The code in the `src/desk/` folder includes specific modifications to accommodate the routing logic required by this study.

To learn about the framework's original architecture and all its features, visit the repository (https://github.com/joaoflavioufmg/desk)

## References
[1] ALMEIDA, João Flávio de Freitas. DESK: Discrete Event Simulation Kit. PPGEP-UFMG; Zenodo, 2025. Disponível em: https://desk-sim.readthedocs.io/en/latest/. DOI: 10.5281/zenodo.18088013.

---