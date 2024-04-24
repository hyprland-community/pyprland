{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    poetry2nix.url = "github:nix-community/poetry2nix";
    systems.url = "github:nix-systems/default";
  };

  outputs = {
    self,
    nixpkgs,
    systems,
    poetry2nix,
  }: let
    inherit (nixpkgs.lib) cleanSource;
    inherit (poetry2nix.lib) mkPoetry2Nix;

    selfClean = cleanSource self;

    supportedSystems = nixpkgs.lib.genAttrs (import systems);
    pkgsFor = system: nixpkgs.legacyPackages.${system};
  in {
    packages = supportedSystems (system: let
      inherit (mkPoetry2Nix {pkgs = pkgsFor system;}) mkPoetryApplication;
    in {
      default = mkPoetryApplication {
        projectDir = selfClean;
        checkGroups = [];
      };
    });

    devShells = supportedSystems (system: let
      inherit (mkPoetry2Nix {pkgs = pkgsFor system;}) mkPoetryEnv;
    in {
      default = (pkgsFor system).mkShellNoCC {
        packages = with (pkgsFor system); [
          (mkPoetryEnv {projectDir = selfClean;})
          poetry
        ];
      };
    });
  };
}
