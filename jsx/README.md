# Jupyterhub Admin Dashboard - React Variant  
This repository contains current updates to the Jupyterhub Admin Dashboard service, 
reducing the complexity from a mass of templated HTML to a simple React web application.
This will integrate with Jupyterhub, speeding up client interactions while simplifying the 
admin dashboard codebase.  

### Build Commands  
- `yarn build`: Installs all dependencies and bundles the application  
- `yarn hot`: Bundles the application and runs a mock (serverless) version on port 8000  
- `yarn lint`: Lints JSX with ESLint  
- `yarn lint --fix`: Lints and fixes errors JSX with ESLint / formats with Prettier  
- `yarn place`: Copies the transpiled React bundle to /share/jupyterhub/static/js/admin-react.js for use.