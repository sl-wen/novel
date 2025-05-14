import { Cheerio, Element, CheerioOptions } from 'cheerio';

declare module 'cheerio' {
  namespace cheerio {
    interface Element {
      type: string;
      name: string;
      attribs: {[attr: string]: string};
      children: any[];
      parent: any;
      next: any;
      prev: any;
    }

    interface CheerioAPI {
      (selector: string): Cheerio<Element>;
      (selector: string, context: string): Cheerio<Element>;
      (selector: string, context: Element): Cheerio<Element>;
      (selector: string, context: Element[]): Cheerio<Element>;
      (selector: string, context: Cheerio<Element>): Cheerio<Element>;
      (selector: Element): Cheerio<Element>;
      (selector: Element[]): Cheerio<Element>;
      (selector: Cheerio<Element>): Cheerio<Element>;
      (selector: string, context: string, root: string | Element | Cheerio<Element>): Cheerio<Element>;
      (): Cheerio<Element>;
      load(html: string): CheerioAPI;
      xml(xml: string): string;
      html(): string;
      root(): Cheerio<Element>;
      contains(container: Element, contained: Element): boolean;
      find(selector: string): Cheerio<Element>;
      text(): string;
      attr(name: string): string | undefined;
      each(func: (index: number, element: Element) => void): Cheerio<Element>;
      remove(): Cheerio<Element>;
    }

    interface Cheerio<T> {
      find(selector: string): Cheerio<Element>;
      text(): string;
      html(): string | null;
      attr(name: string): string | undefined;
      each(func: (index: number, element: T) => void): Cheerio<T>;
      eq(index: number): Cheerio<T>;
      first(): Cheerio<T>;
      last(): Cheerio<T>;
      length: number;
      remove(): Cheerio<T>;
    }
  }

  export function load(html: string, options?: any): cheerio.CheerioAPI;
  export const version: string;
} 