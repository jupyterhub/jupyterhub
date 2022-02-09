const webpack = require("webpack");
const path = require("path");
const express = require("express");

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
    path: path.resolve(__dirname, "build"),
  },
  resolve: {
    extensions: [".css", ".js", ".jsx"],
  },
  plugins: [new webpack.HotModuleReplacementPlugin()],
  devServer: {
    contentBase: path.resolve(__dirname, "build"),
    port: 9000,
    before: (app, server) => {
      var user_data = JSON.parse(
        '[{"kind":"user","name":"foo","admin":true,"groups":[],"server":"/user/foo/","pending":null,"created":"2020-12-07T18:46:27.112695Z","last_activity":"2020-12-07T21:00:33.336354Z","servers":{"":{"name":"","last_activity":"2020-12-07T20:58:02.437408Z","started":"2020-12-07T20:58:01.508266Z","pending":null,"ready":true,"state":{"pid":28085},"url":"/user/foo/","user_options":{},"progress_url":"/hub/api/users/foo/server/progress"}}},{"kind":"user","name":"bar","admin":false,"groups":[],"server":null,"pending":null,"created":"2020-12-07T18:46:27.115528Z","last_activity":"2020-12-07T20:43:51.013613Z","servers":{}}]'
      );
      var group_data = JSON.parse(
        '[{"kind":"group","name":"testgroup","users":[]}, {"kind":"group","name":"testgroup2","users":["foo", "bar"]}]'
      );
      app.use(express.json());

      // get user_data
      app.get("/hub/api/users", (req, res) => {
        res
          .set("Content-Type", "application/json")
          .send(JSON.stringify(user_data));
      });
      // get group_data
      app.get("/hub/api/groups", (req, res) => {
        res
          .set("Content-Type", "application/json")
          .send(JSON.stringify(group_data));
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
