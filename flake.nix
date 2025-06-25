{
  description = "Python project with dev and install environments";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;
        pythonPackages = python.pkgs;

        # Define your Python dependencies here
        pythonDeps = with pythonPackages; [
          numpy
        ];

        # Extract version from __init__.py
        versionFromInit = builtins.head (
          builtins.match ".*__version__ = \"([^\"]+)\".*"
            (builtins.readFile ./src/tevclient/__init__.py)
        );

        # Your package derivation
        tevclientProject = pythonPackages.buildPythonPackage rec {
          pname = "tevclient";
          version = versionFromInit;
          format = "pyproject";
          src = ./.;

          propagatedBuildInputs = pythonDeps;

          # Optional: specify build dependencies
          nativeBuildInputs = with pythonPackages; [
            setuptools
            wheel
          ];

          # checkInputs = with pythonPackages; [
          #   pytest
          # ];

          # doCheck = true;
          # checkPhase = ''
          #   pytest
          # '';
        };

      in
      {
        # System installation
        packages.default = tevclientProject;

        # Development environment
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pythonPackages.black
            pythonPackages.build
            pythonPackages.flake8
            pythonPackages.mypy
            pythonPackages.pip
            pythonPackages.pytest
            pythonPackages.setuptools
            pythonPackages.wheel
          ] ++ pythonDeps;
        };
      });
}
