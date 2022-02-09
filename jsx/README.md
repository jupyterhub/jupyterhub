# Jupyterhub Admin Dashboard - React Variant

This repository contains current updates to the Jupyterhub Admin Dashboard,
reducing the complexity from a mass of templated HTML to a simple React web application.
This will integrate with Jupyterhub, speeding up client interactions while simplifying the
admin dashboard codebase.

### Build Commands

- `yarn build`: Installs all dependencies and bundles the application
- `yarn hot`: Bundles the application and runs a mock (serverless) version on port 8000
- `yarn lint`: Lints JSX with ESLint
- `yarn lint --fix`: Lints and fixes errors JSX with ESLint / formats with Prettier
- `yarn place`: Copies the transpiled React bundle to /share/jupyterhub/static/js/admin-react.js for use.

### Good To Know

Just some basics on how the React Admin app is built.

#### General build structure:

This app is written in JSX, and then transpiled into an ES5 bundle with Babel and Webpack. All JSX components are unit tested with a mixture of Jest and Enzyme and can be run both manually and per-commit. Most logic is separated into components under the `/src/components` directory, each directory containing a `.jsx`, `.test.jsx`, and sometimes a `.css` file. These components are all pulled together, given client-side routes, and connected to the Redux store in `/src/App.jsx` which serves as an entrypoint to the application.

#### Centralized state and data management with Redux:

The app use Redux throughout the components via the `useSelector` and `useDispatch` hooks to store and update user and group data from the API. With Redux, this data is available to any connected component. This means that if one component recieves new data, they all do.

#### API functions

All API functions used by the front end are packaged as a library of props within `/src/util/withAPI.js`. This keeps our web service logic separate from our presentational logic, allowing us to connect API functionality to our components at a high level and keep the code more modular. This connection specifically happens in `/src/App.jsx`, within the route assignments.

#### Pagination

Indicies of paginated user and group data is stored in a `page` variable in the query string, as well as the `user_page` / `group_page` state variables in Redux. This allows the app to maintain two sources of truth, as well as protect the admin user's place in the collection on page reload. Limit is constant at this point and is held in the Redux state.

On updates to the paginated data, the app can respond in one of two ways. If a user/group record is either added or deleted, the pagination will reset and data will be pulled back with no offset. Alternatively, if a record is modified, the offset will remain and the change will be shown.

Code examples:

```js
// Pagination limit is pulled in from Redux.
var limit = useSelector((state) => state.limit);

// Page query string is parsed and checked
var page = parseInt(new URLQuerySearch(props.location).get("page"));
page = isNaN(page) ? 0 : page;

// A slice is created representing the records to be returned
var slice = [page * limit, limit];

// A user's notebook server status was changed from stopped to running, user data is being refreshed from the slice.
startServer().then(() => {
  updateUsers(...slice)
    // After data is fetched, the Redux store is updated with the data and a copy of the page number.
    .then((data) => dispatchPageChange(data, page));
});

// Alternatively, a new user was added, user data is being refreshed from offset 0.
addUser().then(() => {
  updateUsers(0, limit)
    // After data is fetched, the Redux store is updated with the data and asserts page 0.
    .then((data) => dispatchPageChange(data, 0));
});
```
