{
  inputs = {
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";
    systems.url = "github:nix-systems/default";
    devenv.url = "github:cachix/devenv";
    devenv.inputs.nixpkgs.follows = "nixpkgs";
  };

  nixConfig = {
    extra-trusted-public-keys = "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=";
    extra-substituters = "https://devenv.cachix.org";
  };

  outputs = { self, nixpkgs, devenv, systems, ... } @ inputs:
    let
      forEachSystem = nixpkgs.lib.genAttrs (import systems);
    in
    rec {
      packages = forEachSystem (system: {
        devenv-up = self.devShells.${system}.default.config.procfileScript;
        devenv-test = self.devShells.${system}.default.config.test;
      });
      barkoder = forEachSystem (system:
        let pkgs = nixpkgs.legacyPackages.${system}; in pkgs.callPackage ./barkoder/default.nix {
          pybind11 = pkgs.python313Packages.pybind11;
        }
      );

      devShells = forEachSystem
        (system:
          let
            pkgs = nixpkgs.legacyPackages.${system};
          in
          rec {
            default = devenv.lib.mkShell {
              inherit inputs pkgs;
              modules = [
                {
                  # https://devenv.sh/reference/options/
                  languages.python = {
                    enable = true;
                    package = pkgs.python313;
                    libraries = [
                      # Required for Barkoder
                      barkoder.${system}

                      # Required for OpenCV
                      pkgs.libGL
                      pkgs.glib

                      # Required for python-ldap
                      pkgs.openldap
                      pkgs.cyrus_sasl
                    ];


                    venv = {
                      enable = true;
                      requirements = builtins.readFile ./requirements.txt;
                    };
                  };

                  env = {
                    DJANGO_SETTINGS_MODULE = "vdv_pkpass.settings_dev";
                  };
                  packages = [
                    pkgs.openldap
                    pkgs.cyrus_sasl
                  ];

                  enterShell = ''
                  '';

                  scripts._link_system_python_ldap.exec = ''
                    PATH=:$PATH:
                    PATH=''${PATH//:$VIRTUAL_ENV\/bin:/:}
                    PATH=''${PATH#:}
                    PATH=''${PATH%:}
                    echo $PATH
                    which python3
                  '';
                  scripts.initialise.exec = ''
                    mkdir -p ./uic-data
                    mkdir -p ./vdv-certs

                    echo Running Migrations
                    python manage.py migrate

                    echo Downloading UIC Data
                    python manage.py download-uic-data

                    echo Downloading VDV Certs
                    python manage.py download-vdv-certs

                    echo Downloading VDB Orgs
                    python manage.py download-vdv-orgs
                  '';
                }
              ];
            };
          });
    };
}
