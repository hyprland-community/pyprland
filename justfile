pyenv := ".tox/py312-linting"


testenv := ".tox/coverage"

test *params='tests':
    {{testenv}}/bin/coverage erase
    {{testenv}}/bin/coverage run -m pytest --pdb -s {{params}}
    {{testenv}}/bin/coverage report


all:
    tox run -e unit,linting,wiki

compgen:
    tox run -e shellgen

lint:
    tox run -e linting,deadcode

vreg:
    tox run -e vreg

doc:
    tox run -e doc

wiki:
    tox run -e wiki

release:
    ./scripts/make_release

htmlcov:
    {{pyenv}}/bin/coverage html
    xdg-open ./htmlcov/index.html

types:
    {{pyenv}}/bin/mypy --check-untyped-defs pyprland

