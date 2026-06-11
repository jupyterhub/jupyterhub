#!/bin/bash
VENV="$(dirname "$0")/venv"
SHARE="$(dirname "$0")/share/jupyterhub/static"
STATIC_IMG="$SHARE/img/logo-estin.png"
echo "=== Setup UI SAIEP ==="
echo "[1/4] Favicon JupyterHub..."
python3 -c "
from PIL import Image
img = Image.open('$STATIC_IMG')
img = img.resize((32, 32))
img.save('$SHARE/favicon.ico', format='ICO')
"
echo "[2/4] Favicon JupyterLab..."
python3 -c "
from PIL import Image
img = Image.open('$STATIC_IMG')
img = img.resize((32, 32))
img.save('$VENV/lib/python3.12/site-packages/jupyter_server/static/favicon.ico', format='ICO')
img.save('$VENV/lib/python3.12/site-packages/jupyter_server/static/favicons/favicon.ico', format='ICO')
"
echo "[3/4] Personnalisation JupyterLab..."
INDEX="$VENV/share/jupyter/lab/static/index.html"
cp "$INDEX" "$INDEX.bak"
sed -i 's|</head>|<style>#jupyterlab-splash{display:none !important;} #jp-MainLogo svg{display:none !important;} #jp-MainLogo{background-image:url("/hub/static/img/logo-estin.png") !important; background-size:contain !important; background-repeat:no-repeat !important; background-position:center !important; width:80px !important; height:28px !important;} .jp-SideBar{background-color:#34495E !important;} .lm-TabBar.jp-SideBar .lm-TabBar-tab{color:#fff !important;} .jp-Toolbar{background-color:#ffffff !important; border-bottom:3px solid #E54C3F !important;} .jp-MenuBar{background-color:#34495E !important;} .jp-MenuBar-item span{color:#fff !important;} .lm-MenuBar-item span{color:#fff !important;} .jp-MenuBar-item:hover{background-color:#E54C3F !important;} :root{--jp-brand-color0:#E54C3F !important; --jp-brand-color1:#E54C3F !important; --jp-brand-color2:#34495E !important; --jp-brand-color3:#34495E !important;}</style></head>|' "$INDEX"
sed -i 's|<title>JupyterLab</title>|<title>ESTIN - SAIEP</title>|' "$INDEX"
echo "[4/4] Titre JupyterHub..."
sed -i 's|<title>JupyterHub</title>|<title>ESTIN - SAIEP</title>|' "$(dirname "$0")/share/jupyterhub/templates/page.html" 2>/dev/null || true
echo "=== Done ! Restart JupyterHub to apply ==="
