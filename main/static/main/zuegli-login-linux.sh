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
MimeType=x-scheme-handler/dbnav;x-scheme-handler/bahnbonus;x-scheme-handler/de.eosuptrade.avvshop;x-scheme-handler/vestische;x-scheme-handler/bvr;x-scheme-handler/classic;x-scheme-handler/sobus;x-scheme-handler/bogestra;x-scheme-handler/dsw21;x-scheme-handler/dvg;x-scheme-handler/hst;x-scheme-handler/hcr;x-scheme-handler/moebus;x-scheme-handler/viersen;x-scheme-handler/niag;x-scheme-handler/evag;x-scheme-handler/mvg;x-scheme-handler/sdg;x-scheme-handler/swn;x-scheme-handler/swr;x-scheme-handler/stoag;x-scheme-handler/swk;x-scheme-handler/ver
EOF

xdg-mime default zuegli-hook.desktop x-scheme-handler/dbnav
xdg-mime default zuegli-hook.desktop x-scheme-handler/bahnbonus
xdg-mime default zuegli-hook.desktop x-scheme-handler/de.eosuptrade.avvshop
xdg-mime default zuegli-hook.desktop x-scheme-handler/vestische
xdg-mime default zuegli-hook.desktop x-scheme-handler/classic
xdg-mime default zuegli-hook.desktop x-scheme-handler/sobus
xdg-mime default zuegli-hook.desktop x-scheme-handler/bvr
xdg-mime default zuegli-hook.desktop x-scheme-handler/bogestra
xdg-mime default zuegli-hook.desktop x-scheme-handler/dsw21
xdg-mime default zuegli-hook.desktop x-scheme-handler/dvg
xdg-mime default zuegli-hook.desktop x-scheme-handler/hst
xdg-mime default zuegli-hook.desktop x-scheme-handler/hcr
xdg-mime default zuegli-hook.desktop x-scheme-handler/moebus
xdg-mime default zuegli-hook.desktop x-scheme-handler/viersen
xdg-mime default zuegli-hook.desktop x-scheme-handler/niag
xdg-mime default zuegli-hook.desktop x-scheme-handler/evag
xdg-mime default zuegli-hook.desktop x-scheme-handler/mvg
xdg-mime default zuegli-hook.desktop x-scheme-handler/sdg
xdg-mime default zuegli-hook.desktop x-scheme-handler/swn
xdg-mime default zuegli-hook.desktop x-scheme-handler/swr
xdg-mime default zuegli-hook.desktop x-scheme-handler/stoag
xdg-mime default zuegli-hook.desktop x-scheme-handler/swk
xdg-mime default zuegli-hook.desktop x-scheme-handler/ver

sudo update-desktop-database ~/.local/share/applications

echo "Install complete ✨"
