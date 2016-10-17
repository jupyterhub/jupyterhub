// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import {
  Menu
} from 'phosphor/lib/ui/menu';

import {
  getBaseUrl, getConfigOption
} from '@jupyterlab/services/lib/utils';

import {
  ICommandPalette
} from 'jupyterlab/lib/commandpalette';

import {
  IMainMenu
} from 'jupyterlab/lib/mainmenu';

import {
  JupyterLab, JupyterLabPlugin
} from 'jupyterlab/lib/application';

import * as urljoin
  from 'url-join';


/**
 * Activate the jupyterhub extension.
 */
function activateHubExtension(app: JupyterLab, palette: ICommandPalette, mainMenu: IMainMenu): void {

  // This config is provided by JupyterHub to the single-user server app.
  // The app passes in jinja template variables which populate lab.html.
  let hubHost = getConfigOption('hubHost');
  let hubPrefix = getConfigOption('hubPrefix');

  if (!hubPrefix) {
    console.log('No JupyterHub configuration found.');
    return
  }

  console.log('JupyterHub configuration found: ' + hubHost + hubPrefix);

  let { commands, keymap } = app;
  let category = 'Hub';

  let menu = new Menu({ commands, keymap });
  menu.title.label = 'Hub';

  let command: string;

  // Add commands and menu itmes for each link.
  command = 'hub:control-panel';
  commands.addCommand(command, {
    label: 'Control Panel',
    execute: () => {
      window.open(hubHost + urljoin(hubPrefix, 'home'), '_blank');
    }
  });
  palette.addItem({command: command, category: "Hub"});
  menu.addItem({ command });

  command = 'hub:logout';
  commands.addCommand(command, {
    label: 'Logout',
    execute: () => {
      window.open(hubHost + urljoin(hubPrefix, 'logout'), '_blank');
    }
  });
  palette.addItem({command: command, category: "Hub"});
  menu.addItem({ command });

  mainMenu.addMenu(menu, {rank: 100});
}


/**
 * Initialization data for the jupyterlab_hub extension.
 */
const hubExtension: JupyterLabPlugin<void> = {
  id: 'jupyter.extensions.hub',
  requires: [
    ICommandPalette,
    IMainMenu,
  ],
  activate: activateHubExtension,
  autoStart: true,
  }

export default hubExtension;
