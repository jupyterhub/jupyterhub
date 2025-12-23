// Workaround "ReferenceError: TextEncoder is not defined"
// https://stackoverflow.com/questions/68468203/why-am-i-getting-textencoder-is-not-defined-in-jest/68468204#68468204
// https://jestjs.io/docs/configuration#setupfiles-array
import { TextEncoder, TextDecoder } from "util";
Object.assign(global, { TextDecoder, TextEncoder });
