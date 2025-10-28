module.exports = {
  // Basic formatting
  printWidth: 80,
  tabWidth: 2,
  useTabs: false,
  semi: false,
  singleQuote: true,
  quoteProps: 'as-needed',

  // JSX
  jsxSingleQuote: true,

  // Trailing commas
  trailingComma: 'es5',

  // Brackets
  bracketSpacing: true,
  bracketSameLine: false,
  arrowParens: 'avoid',

  // Prose wrap
  proseWrap: 'preserve',

  // HTML whitespace
  htmlWhitespaceSensitivity: 'css',

  // Vue files
  vueIndentScriptAndStyle: false,

  // Line endings
  endOfLine: 'lf',

  // Embedded language formatting
  embeddedLanguageFormatting: 'auto',

  // Override for specific file types
  overrides: [
    {
      files: '*.md',
      options: {
        proseWrap: 'always',
        printWidth: 100,
      },
    },
    {
      files: '*.json',
      options: {
        printWidth: 100,
      },
    },
    {
      files: '*.{css,scss,less}',
      options: {
        singleQuote: false,
      },
    },
  ],
}
