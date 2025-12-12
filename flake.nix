{
  description = "A flake.nix file for coffee-rt";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python3
            uv
            just
            postgresql
            nodejs
            yarn
            redis
            kubernetes-helm
            kubectl
            terragrunt
            openjdk17
            maven
            azure-cli
          ];
        };
        shellHook = ''
          export PATH=${pkgs.maven}/bin:$PATH
        '';
      }
    );
}
