import { defineConfig } from "eslint/config";
import react from "eslint-plugin-react";
import prettier from "eslint-plugin-prettier";
import unusedImports from "eslint-plugin-unused-imports";
import globals from "globals";
import path from "node:path";
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: js.configs.recommended,
  allConfig: js.configs.all,
});

export default defineConfig([
  {
    extends: compat.extends("plugin:react/recommended"),

    plugins: {
      react,
      prettier,
      "unused-imports": unusedImports,
    },

    languageOptions: {
      globals: {
        ...globals.browser,
      },

      ecmaVersion: 2018,
      sourceType: "module",

      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },

    settings: {
      react: {
        version: "detect",
      },
    },

    rules: {
      semi: "off",
      quotes: "off",
      "prettier/prettier": "warn",
      "no-unused-vars": "off",
      "unused-imports/no-unused-imports": "error",

      "unused-imports/no-unused-vars": [
        "warn",
        {
          vars: "all",
          varsIgnorePattern: "^regeneratorRuntime|^_",
          args: "after-used",
          argsIgnorePattern: "^_",
        },
      ],
    },
  },
  {
    files: ["**/*.test.js", "**/*.test.jsx"],

    languageOptions: {
      globals: {
        ...globals.jest,
      },
    },
  },
]);
