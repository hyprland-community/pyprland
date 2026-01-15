pyenv := ".tox/py314-linting"
testenv := ".tox/py314-unit"

test *params='tests':
    {{testenv}}/bin/pytest --pdb -s {{params}}

all:
    tox run -e unit,linting,wiki

website:
    npm i
    npm run docs:dev

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
    tox run -e coverage
    {{pyenv}}/bin/coverage html
    xdg-open ./htmlcov/index.html

types:
    {{pyenv}}/bin/mypy --check-untyped-defs pyprland
