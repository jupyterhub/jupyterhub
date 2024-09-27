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
        exclude: /node_modules/,
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
    static: ["build", "testing", "../share/jupyterhub"],
    port: 9000,
    onBeforeSetupMiddleware: (devServer) => {
      const app = devServer.app;

      // get user_data
      app.get("/hub/api/users", (req, res) => {
        res.set("Content-Type", "application/json").send(user_json);
      });
      // get group_data
      app.get("/hub/api/groups", (req, res) => {
        res.set("Content-Type", "application/json").send(group_json);
      });
      // add users to group
      app.post("/hub/api/groups/*/users", (req, res) => {
        console.log(req.url, req.body);
        res.status(200).end();
      });
      // remove users from group
      app.delete("/hub/api/groups/*", (req, res) => {
        console.log(req.url, req.body);
        res.status(200).end();
      });
      // add users
      app.post("/hub/api/users", (req, res) => {
        console.log(req.url, req.body);
        res.status(200).end();
      });
      // delete user
      app.delete("/hub/api/users", (req, res) => {
        console.log(req.url, req.body);
        res.status(200).end();
      });
      // start user server
      app.post("/hub/api/users/*/server", (req, res) => {
        console.log(req.url, req.body);
        res.status(200).end();
      });
      // stop user server
      app.delete("/hub/api/users/*/server", (req, res) => {
        console.log(req.url, req.body);
        res.status(200).end();
      });
      // shutdown hub
      app.post("/hub/api/shutdown", (req, res) => {
        console.log(req.url, req.body);
        res.status(200).end();
      });
    },
  },
};
