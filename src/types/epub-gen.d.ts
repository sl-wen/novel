declare module 'epub-gen' {
  interface EpubOptions {
    title: string;
    author: string;
    publisher?: string;
    cover?: string;
    content: Array<{
      title: string;
      data: string;
    }>;
    verbose?: boolean;
    tocTitle?: string;
    version?: string;
    description?: string;
    appendChapterTitles?: boolean;
    customHtmlTocTemplatePath?: string;
    lang?: string;
    css?: string;
    fontPath?: string;
    fonts?: string[];
    ignoreFailedDownloads?: boolean;
    date?: string;
    uuid?: string;
  }

  class EpubGenerator {
    constructor(options: EpubOptions, outputPath: string);
    promise: Promise<void>;
  }

  export default EpubGenerator;
} 