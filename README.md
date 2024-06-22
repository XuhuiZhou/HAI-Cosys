![TITLE](figs/title.png)
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

penAI key is required to run the code. Please set the environment variable `OPENAI_API_KEY` to your key. The recommend way is to add the key to the conda environment:
```bash
conda env config vars set OPENAI_API_KEY=your_key
```

A redis-stack server is required to run the code.
Here are four lines of code to create a redis-stack server:
```bash
curl -fsSL https://packages.redis.io/redis-stack/redis-stack-server-7.2.0-v10.focal.x86_64.tar.gz -o redis-stack-server.tar.gz
tar -xvf redis-stack-server.tar.gz
pip install redis
./redis-stack-server-7.2.0-v10/bin/redis-stack-server --daemonize yes
```

The `REDIS_OM_URL` need to be set before loading and saving agents:
```bash
conda env config vars set REDIS_OM_URL="redis://user:password@host:port"
```

## Contribution
### Install dev options
```bash
mypy --install-types --non-interactive haicosystem
pip install pre-commit
pre-commit install
```
### New branch for each feature
`git checkout -b feature/feature-name` and PR to `main` branch.
### Before committing
Run `pytest` to make sure all tests pass (this will ensure dynamic typing passed with beartype) and `mypy --strict .` to check static typing.
(You can also run `pre-commit run --all-files` to run all checks)
### Check github action result
Check the github action result to make sure all tests pass. If not, fix the errors and push again.