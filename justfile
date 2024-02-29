default: (test_quick "")

test_quick *params:
    .tox/py311/bin/coverage run -m pytest --pdb -s {{params}}
    .tox/py311/bin/coverage report

doc:
    tox run -e doc

wiki:
    tox run -e wiki

test:
    tox run

release:
    ./scripts/make_release
