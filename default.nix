(
  import
  (
    let
      lock = builtins.fromJSON (builtins.readFile ./flake.lock);
      nodeName = lock.nodes.root.inputs.flake-compat;
    in
      fetchTarball {
        url = lock.nodes.${nodeName}.locked.url or "https://github.com/hyprland-community/pyprland/archive/${lock.nodes.flake-compat.locked.rev}.tar.gz";
        sha256 = lock.nodes.${nodeName}.locked.narHash;
      }
  )
  {src = ./.;}
)
