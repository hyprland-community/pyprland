# Nix

You are recommended to get the latest pyprland package from the [flake.nix](https://github.com/hyprland-community/pyprland/blob/main/flake.nix)
provided within this repository. To use it in your system, you may add pyprland
to your flake inputs.

## Flake

```nix
## flake.nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyprland.url = "github:hyprland-community/pyprland";
  };

  outputs = { self, nixpkgs, pyprland, ...}: let
  in {
    nixosConfigurations.<yourHostname> = nixpkgs.lib.nixosSystem {
      #         remember to replace this with your system arch ↓
      environment.systemPackages = [ pyprland.packages."x86_64-linux".pyprland ];
      # ...
    };
  };
}
```

Alternatively, if you are using the Nix package manager but not NixOS as your
main distribution, you may use `nix profile` tool to install pyprland from this
repository using the following command.

```bash
nix profile install github:nix-community/pyprland
```

The package will now be in your latest profile. You may use `nix profile list`
to verify your installation.

## Nixpkgs

Pyprland is available under nixpkgs, and can be installed by adding
`pkgs.pyprland` to either `environment.systemPackages` or `home.packages`
depending on whether you want it available system-wide or to only a single
user using home-manager. If the derivation available in nixpkgs is out-of-date
then you may consider using `overrideAttrs` to update the source locally.

```nix
let
  pyprland = pkgs.pyprland.overrideAttrs {
    version = "your-version-here";
    src = fetchFromGitHub {
      owner = "hyprland-community";
      repo = "pyprland";
      rev = "tag-or-revision";
      # leave empty for the first time, add the new hash from the error message
      hash = "";
    };
  };
in {
  # add the overridden package to systemPackages
  environment.systemPackages = [pyprland];
}
```
