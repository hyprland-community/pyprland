def test_templates():
    "test the template function"
    from pyprland.common import apply_variables

    assert (
        apply_variables("[one] $var [two] ${var2} [three]", {"one": "X", "three": "Y"})
        == "X $var [two] ${var2} Y"
    )
