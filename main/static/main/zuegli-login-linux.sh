#!/usr/bin/env bash

set -e

mkdir -p ~/.local/bin
mkdir -p ~/.local/share/applications

cat > ~/.local/bin/zuegli-hook <<EOF
#!/usr/bin/env bash

url=\$(echo -n \$1 | base64)
xdg-open "https://xn--zgli-0ra.app/account/oauth_callback?url=\$url"
EOF
chmod +x ~/.local/bin/zuegli-hook

cat > ~/.local/share/applications/zuegli-hook.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Zügli Login Hook
Exec=/bin/sh -c "$HOME/.local/bin/zuegli-hook %u"
StartupNotify=false
MimeType=x-scheme-handler/dbnav;x-scheme-handler/bahnbonus;x-scheme-handler/de.eosuptrade.avvshop;x-scheme-handler/vestische;x-scheme-handler/bvr;x-scheme-handler/classic;x-scheme-handler/sobus;
EOF

xdg-mime default zuegli-hook.desktop x-scheme-handler/dbnav
xdg-mime default zuegli-hook.desktop x-scheme-handler/bahnbonus
xdg-mime default zuegli-hook.desktop x-scheme-handler/de.eosuptrade.avvshop
xdg-mime default zuegli-hook.desktop x-scheme-handler/vestische
xdg-mime default zuegli-hook.desktop x-scheme-handler/classic
xdg-mime default zuegli-hook.desktop x-scheme-handler/sobus
xdg-mime default zuegli-hook.desktop x-scheme-handler/bvr

echo "Install complete ✨"
