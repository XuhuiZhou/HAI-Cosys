![TITLE](data/title.png)
# HAICOSYSTEM
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3109/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![bear-ified](https://raw.githubusercontent.com/beartype/beartype-assets/main/badge/bear-ified.svg)](https://beartype.readthedocs.io)


## Get started

This package supports Python 3.11 and above. We recommend using a virtual environment to install this package, e.g.,

```
conda create -n haicosystem python=3.11; conda activate haicosystem;  curl -sSL https://install.python-poetry.org | python3
poetry install
```

OpenAI key is required to run the code. Please set the environment variable `OPENAI_API_KEY` to your key. The recommend way is to add the key to the conda environment:
```bash
conda env config vars set OPENAI_API_KEY=your_key
```

A redis-stack server is required to run the code. Please follow the instruction [here](https://docs.sotopia.world/#set-up-redis-stack) to set up the server.



The `REDIS_OM_URL` need to be set before loading and saving agents:
```bash
conda env config vars set REDIS_OM_URL="redis://user:password@host:port"
```

> [!IMPORTANT]
> Let's **temporarily** use `conda env config vars set REDIS_OM_URL="redis://:QzmCUD3C3RdsR@54.146.206.168:6379"


## Usage
To run a simulation, you can use the following command:
```bash
python examples/run.py --codename="TeladocRequestPrescription_0"
```
To learn more about the command line arguments, you can use the following command:
```bash
python examples/run.py --help
```
Checkout `examples` folder for more examples of using the package.

### Upload profiles to the database

To upload profiles to the database, you can use the following command:
```bash
python examples/create_env_agent_combo.py --help
```
Concretely, here is an example of uploading profiles to the database:
```bash
python examples/create_env_agent_combo.py --agent-folder="./assets/ai_agent_profiles" --env-folders="./assets/education,./assets/healthcare,./assets/personal_services,./assets/miscellaneous,./assets/technology_and_science,./assets/business_and_finance" --clean-combos
```
Checkout `examples` folder for more examples of using the package.

### Run scaled simulations

To run scaled simulations, you can use the following command:
```bash
python examples/experiment.py --help
```
Concretely, here is an example of running scaled simulations:
```bash
python examples/run_scaled_simulation.py --agent-folder="./assets/ai_agent_profiles" --env-folders="./assets/education,./assets/healthcare,./assets/personal_services,./assets/miscellaneous,./assets/technology_and_science,./assets/business_and_finance" --num-simulations=10 --num-agents=10 --num-envs=10
```

## Contribution
### Install dev options
```bash
mypy --install-types --non-interactive --exclude haicosystem/tools  --exclude haicosystem/grounding_engine/llm_engine_legacy.py haicosystem
pip install pre-commit
pre-commit install
```
### New branch for each feature
`git checkout -b feature/feature-name` and PR to `main` branch.
### Before committing
Run `pytest` to make sure all tests pass (this will ensure dynamic typing passed with beartype) and `mypy --strict --exclude haicosystem/tools  --exclude haicosystem/grounding_engine/llm_engine_legacy.py .` to check static typing.
(You can also run `pre-commit run --all-files` to run all checks)
### Check github action result
Check the github action result to make sure all tests pass. If not, fix the errors and push again.
