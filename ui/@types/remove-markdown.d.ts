declare module '@tommoor/remove-markdown' {
  /**
 * Strip Markdown formatting from text
 * @param markdown Markdown text
 */
  function RemoveMarkdown(markdown: string, options?: {
    stripListLeaders?: boolean | undefined;
    listUnicodeChar?: string | undefined;
    gfm?: boolean | undefined;
    useImgAltText?: boolean | undefined;
}): string;

  export = RemoveMarkdown;
}