#!/usr/bin/env bash

set -e

mkdir -p ~/.local/bin
mkdir -p ~/.local/share/applications

cat > ~/.local/bin/db-hook <<EOF
#!/usr/bin/env bash

if [[ "\$1" == "dbnav:"* ]]; then
  url=\$(echo -n \$1 | base64)
  xdg-open "https://vdv-pkpass.magicalcodewit.ch/account/db_login/callback?url=\$url"
elif [[ "\$1" == "bahnbonus:"* ]]; then
  url=\$(echo -n \$1 | base64)
  xdg-open "https://vdv-pkpass.magicalcodewit.ch/account/bahnbonus_login/callback?url=\$url"
elif [[ "\$1" == "de.eosuptrade.avvshop:"* ]]; then
  url=\$(echo -n \$1 | base64)
  xdg-open "https://vdv-pkpass.magicalcodewit.ch/account/avv_login/callback?url=\$url"
else
  xdg-open "\$1"
fi
EOF
chmod +x ~/.local/bin/db-hook

cat > ~/.local/share/applications/dbnav.desktop <<EOF
[Desktop Entry]
Type=Application
Name=VDV PKPass DB Navigator Hook
Exec=/bin/sh -c "$HOME/.local/bin/db-hook %u"
StartupNotify=false
MimeType=x-scheme-handler/dbnav;x-scheme-handler/bahnbonus;x-scheme-handler/de.eosuptrade.avvshop;
EOF

xdg-mime default dbnav.desktop x-scheme-handler/dbnav
xdg-mime default dbnav.desktop x-scheme-handler/bahnbonus
xdg-mime default dbnav.desktop x-scheme-handler/de.eosuptrade.avvshop

echo "Install complete ✨"
