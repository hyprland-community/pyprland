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
              env.HATCH_METADATA_CLASSIFIERS_NO_VERIFY = "1";
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

          getDependencies = project.renderers.withPackages { inherit python; };
          pythonWithPackages = python.withPackages getDependencies;
        in
        {
          default = self.devShells.${system}.pyprland;
          pyprland = pkgs.mkShell {
            packages = [
              pythonWithPackages
              pkgs.uv
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
