{
  description = "AppDaemon Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      nixpkgsFor = forAllSystems (system: import nixpkgs { inherit system; });
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgsFor.${system};
          pythonEnv = pkgs.python3.withPackages (ps: with ps; [
            appdaemon
            requests
          ]);
        in
        {
          default = pkgs.mkShell {
            buildInputs = [
              pythonEnv
              pkgs.wakeonlan
            ];

            shellHook = ''
              echo "============================================="
              echo "🛡️ AppDaemon Development Environment Loaded 🛡️"
              echo "Python version: $(python3 --version)"
              echo "Available modules: appdaemon, requests"
              echo "============================================="
            '';
          };
        });
    };
}
