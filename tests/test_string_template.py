def test_templates():
    "test the template function"
    from pyprland.common import apply_variables

    assert (
        apply_variables("[one] $var [two] ${var2} [three]", {"one": "X", "three": "Y"})
        == "X $var [two] ${var2} Y"
    )
    assert (
        apply_variables(
            "[one thing] $one one [one] ${var2} [one other thing] [one] [one thing]",
            {"one": "X", "one thing": "Y"},
        )
        == "Y $one one X ${var2} [one other thing] X Y"
    )
