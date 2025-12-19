pyenv := ".tox/py313-linting"
testenv := ".tox/py313-unit"

test *params='tests':
    {{testenv}}/bin/pytest --pdb -s {{params}}

all:
    tox run -e unit,linting,wiki

website:
    npm i
    npm run docs:dev

compgen:
    tox run -e shellgen

lint: stubs
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

types: stubs
    {{pyenv}}/bin/mypy --check-untyped-defs pyprland

stubs:
    stubgen --include-private -m PIL -p PIL.Image -p PIL.ImageDraw -p PIL.ImageOps -o type_stubs
