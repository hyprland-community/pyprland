{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";

    # <https://github.com/pyproject-nix/pyproject.nix>
    pyproject-nix = {
      url = "github:nix-community/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # <https://github.com/nix-systems/nix-systems>
    systems.url = "github:nix-systems/default-linux";

    # <https://github.com/edolstra/flake-compat>
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      pyproject-nix,
      systems,
      ...
    }:
    let
      eachSystem = nixpkgs.lib.genAttrs (import systems);
      pkgsFor = eachSystem (system: nixpkgs.legacyPackages.${system});
      project = pyproject-nix.lib.project.loadPyproject {
        projectRoot = ./.;
      };
    in
    {
      packages = eachSystem (
        system:
        let
          pkgs = pkgsFor.${system};
          python = pkgs.python3;

          attrs = project.renderers.buildPythonPackage { inherit python; };
        in
        {
          default = self.packages.${system}.pyprland;
          pyprland = python.pkgs.buildPythonPackage (
            attrs
            // {
              postPatch = ''
                                  ${pkgs.lib.getExe' pkgs.gnused "sed"} -i 's/email = "fdev31 <fdev31@gmail.com>"/email = "fdev31@gmail.com"/' pyproject.toml
                                  ${pkgs.lib.getExe' pkgs.gnused "sed"} -i '/^\[build-system\]/,/^build-backend.*$/c\
                [build-system]\
                requires = ["hatchling"]\
                build-backend = "hatchling.build"' pyproject.toml
              '';

              nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [
                python.pkgs.hatchling
              ];
            }
          );
        }
      );

      devShells = eachSystem (
        system:
        let
          pkgs = pkgsFor.${system};
          python = pkgs.python3;

          devDeps = builtins.attrNames (project.pyproject.tool.poetry.group.dev.dependencies or { });
          getDependencies = project.renderers.withPackages { inherit python; };
          pythonWithPackages = python.withPackages (
            pythonPackages:
            (getDependencies pythonPackages)
            ++ (builtins.filter (x: x != null) (map (name: pythonPackages.${name} or null) devDeps))
          );
        in
        {
          default = self.devShells.${system}.pyprland;
          pyprland = pkgs.mkShell {
            packages = [
              pythonWithPackages
              pkgs.poetry
            ];

          };
        }
      );
    };

  nixConfig = {
    extra-substituters = [ "https://hyprland-community.cachix.org" ];
    extra-trusted-public-keys = [
      "hyprland-community.cachix.org-1:5dTHY+TjAJjnQs23X+vwMQG4va7j+zmvkTKoYuSXnmE="
    ];
  };
}
