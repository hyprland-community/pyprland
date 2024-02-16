{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    poetry2nix.url = "github:nix-community/poetry2nix";
    systems.url = "github:nix-systems/default";
  };

  outputs = {
    self,
    nixpkgs,
    poetry2nix,
    systems,
  }: let
    supportedSystems = nixpkgs.lib.genAttrs (import systems);
  in {
    packages = supportedSystems (system: let
      inherit (poetry2nix.lib.mkPoetry2Nix {pkgs = nixpkgs.legacyPackages.${system};}) mkPoetryApplication;
    in {
      default = mkPoetryApplication {projectDir = self;};
    });

    devShells = supportedSystems (system: let
      inherit (poetry2nix.lib.mkPoetry2Nix {pkgs = nixpkgs.legacyPackages.${system};}) mkPoetryEnv;
    in {
      default = nixpkgs.legacyPackages.${system}.mkShellNoCC {
        packages = with nixpkgs.legacyPackages.${system}; [
          (mkPoetryEnv {projectDir = self;})
          poetry
        ];
      };
    });
  };
}
