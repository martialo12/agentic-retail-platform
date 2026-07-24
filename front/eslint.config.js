import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import ts from 'typescript-eslint'

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.vue'],
    languageOptions: { parserOptions: { parser: ts.parser } },
  },
  {
    rules: {
      'vue/multi-word-component-names': 'off',
      // TypeScript and vue-tsc already resolve identifiers, including browser
      // globals; ESLint's no-undef only double-flags them without a globals list.
      'no-undef': 'off',
    },
  },
]
