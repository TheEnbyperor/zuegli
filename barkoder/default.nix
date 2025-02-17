{ lib
, stdenv
, fixDarwinDylibNames
, curl
, pybind11
, cmake
, buildPackages
}:

stdenv.mkDerivation rec {
  pname = "python-barkoder-sys";
  version = "2.1.28";

  src = ./.;

  outputs = [
    "out"
  ];

  depsBuildBuild = [ buildPackages.stdenv.cc ];
  nativeBuildInputs = [
    cmake
  ] ++ lib.optional stdenv.hostPlatform.isDarwin fixDarwinDylibNames;
  buildInputs = [
    pybind11
    curl
  ];

  #configureFlags = [
  #];

  #env = lib.optionalAttrs stdenv.cc.isGNU {
  #  NIX_CFLAGS_COMPILE = "-Wno-error=implicit-function-declaration";
  #};

  installPhase = ''
    mkdir -p $out/lib
    cp ./Barkoder.cpython-*.so $out/lib/
  '';
  #installFlags = lib.optionals stdenv.hostPlatform.isDarwin [
  #  "framedir=$(out)/Library/Frameworks/SASL2.framework"
  #];

  #passthru.tests = {
  #  inherit (nixosTests) parsedmarc postfix;
  #};

  meta = with lib; {
    homepage = "https://barkoder.com/";
    description = "High-performance mobile and web barcode scanning software from barKoder";
    platforms = platforms.unix;
    license = licenses.unfree;
  };
}
