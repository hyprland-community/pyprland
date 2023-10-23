{
  description = "pyprland";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixos-23.05";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
  flake-utils.lib.eachDefaultSystem
  (system:
  let
    pkgs = import nixpkgs {
      inherit system;
    };
  in
  {
    packages = rec {
      pyprland = pkgs.poetry2nix.mkPoetryApplication {
        projectDir = ./.;
        python = pkgs.python310;
      };
      default = pyprland;
    };
  }
  );
}
