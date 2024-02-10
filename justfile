test_all: test_cover test_lint test_wiki

test_wiki:
    @for n in $(ls -1 pyprland/plugins/*.py | cut -d/ -f3 |grep -vE '(pyprland|experimental|__|interface|_v[0-9]+.py$)' | sed 's#[.]py$#.md#'); do ls wiki/$n; done > /dev/null

test_cover:
    poetry run coverage run -m pytest
    @poetry run coverage report

test_lint:
    poetry run mypy pyprland
    poetry run vulture --ignore-names 'event_*,run_*,from*,instance' pyprland v_whitelist.py
