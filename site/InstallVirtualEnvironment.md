# Virtual env

Even though the best way to get Pyprland installed is to use your operating system package manager,
for some usages or users it can be convenient to use a virtual environment.

This is very easy to achieve in a couple of steps:

```shell
python -m venv ~/pypr-env
~/pypr-env/bin/pip install pyprland
```

**That's all folks!**

The only extra care to take is to use `pypr` from the virtual environment, eg:

- adding `~/pypr-env/bin/` (replace with your environment path) to your `$PATH`
- using the full path to the pypr command (eg: `~/pypr-env/bin/pypr`)
