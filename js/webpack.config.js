const TerserPlugin = require("terser-webpack-plugin");

var path = require("path");
var version = require("./package.json").version;

// Custom webpack rules are generally the same for all webpack bundles, hence
// stored in a separate local variable.
var rules = [
  { test: /\.css$/, use: ["style-loader", "css-loader"] },
  { test: /\.svg$/, use: ["svg-inline-loader"] }
];

var minimize = false;

module.exports = (env, argv) => {
  var devtool = argv.mode === "development" ? "source-map" : false;
  return [
    {
      // Embeddable cad-viewer-widget bundle
      //
      // This bundle is generally almost identical to the notebook bundle
      // containing the custom widget views and models.
      //
      // The only difference is in the configuration of the webpack public path
      // for the static assets.
      //
      // It will be automatically distributed by unpkg to work with the static
      // widget embedder.
      //
      // The target bundle is always `dist/index.js`, which is the path required
      // by the custom widget embedder.
      //
      entry: "./lib/embed.js",
      output: {
        filename: "index.js",
        path: path.resolve(__dirname, "dist"),
        libraryTarget: "amd",
        publicPath: "https://unpkg.com/cad-viewer-widget@" + version + "/dist/"
      },
      devtool,
      optimization: {
        minimize: minimize,
        minimizer: [
          new TerserPlugin({
            parallel: true,
            terserOptions: {
              compress: { defaults: false },
              mangle: true
            }
          })
        ]
      },
      module: {
        rules: rules
      },
      externals: ["@jupyter-widgets/base"]
    }
  ];
};
