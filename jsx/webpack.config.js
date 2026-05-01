const webpack = require("webpack");
const path = require("path");
const user_json = require("./testing/user.json");
const group_json = require("./testing/group.json");

module.exports = {
  entry: path.resolve(__dirname, "src", "App.jsx"),
  mode: "production",
  module: {
    rules: [
      {
        test: /\.(js|jsx)/,
        exclude: /node_modules/,
        use: "babel-loader",
      },
      {
        test: /\.(css)/,
        use: ["style-loader", "css-loader"],
      },
      {
        test: /\.(png|jpe?g|gif|svg|woff2?|ttf)$/i,
        exclude: /node_modules/,
        use: "file-loader",
      },
    ],
  },
  output: {
    publicPath: "/",
    filename: "admin-react.js",
    path: path.resolve(__dirname, "../share/jupyterhub/static/js/"),
  },
  resolve: {
    extensions: [".css", ".js", ".jsx"],
  },
  plugins: [new webpack.HotModuleReplacementPlugin()],
  devServer: {
    client: {
      overlay: false,
    },
    // Serve the mock app shell from `/` during local dev.
    static: ["testing", "build", "../share/jupyterhub"],
    devMiddleware: {
      index: "index.html",
    },
    port: 9000,
    setupMiddlewares: (middlewares, devServer) => {
      const app = devServer.app;
      const apiPrefixes = ["/api", "/hub/api"];
      const forEachApiPrefix = (register) => {
        apiPrefixes.forEach((prefix) => register(prefix));
      };

      // get user_data
      forEachApiPrefix((prefix) => {
        app.get(`${prefix}/users`, (req, res) => {
          res.set("Content-Type", "application/json").send(user_json);
        });
      });
      // get single user_data
      forEachApiPrefix((prefix) => {
        app.get(`${prefix}/users/*`, (req, res) => {
          const username = req.path.split("/").pop();
          const user = (user_json.items || []).find((item) => item.name === username);
          if (user) {
            res.set("Content-Type", "application/json").send(user);
          } else {
            res.status(404).json({ message: `User '${username}' not found` });
          }
        });
      });
      // get group_data
      forEachApiPrefix((prefix) => {
        app.get(`${prefix}/groups`, (req, res) => {
          res.set("Content-Type", "application/json").send(group_json);
        });
      });
      // add users to group
      forEachApiPrefix((prefix) => {
        app.post(`${prefix}/groups/*/users`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
      });
      // remove users from group
      forEachApiPrefix((prefix) => {
        app.delete(`${prefix}/groups/*`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
      });
      // add users
      forEachApiPrefix((prefix) => {
        app.post(`${prefix}/users`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
      });
      // delete user
      forEachApiPrefix((prefix) => {
        app.delete(`${prefix}/users`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
      });
      // start user server
      forEachApiPrefix((prefix) => {
        app.post(`${prefix}/users/*/server`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
      });
      // stop user server
      forEachApiPrefix((prefix) => {
        app.delete(`${prefix}/users/*/server`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
      });
      // start/stop named user servers
      forEachApiPrefix((prefix) => {
        app.post(`${prefix}/users/*/servers/*`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
        app.delete(`${prefix}/users/*/servers/*`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
      });
      // shutdown hub
      forEachApiPrefix((prefix) => {
        app.post(`${prefix}/shutdown`, (req, res) => {
          console.log(req.url, req.body);
          res.status(200).end();
        });
      });
      return middlewares;
    },
  },
};
