import { BaseNovelSource } from './base';
import { RuleConfig } from '../types/rule';

// 这是一个占位符，用于解决导入错误
// 当实际实现时应替换为真正的实现
export class BiqugeSource extends BaseNovelSource {
  constructor() {
    const config: RuleConfig = {
      name: "笔趣阁",
      baseUrl: "https://www.biquge.com",
      searchRule: {
        url: "https://www.biquge.com/search.php?keyword={keyword}",
        list: ".result-list .result-item",
        item: {
          title: ".result-game-item-title-link",
          author: ".result-game-item-info-tag:nth-child(1) span:last-child",
          link: ".result-game-item-title-link"
        }
      },
      bookRule: {
        title: "#info h1",
        author: "#info p:nth-child(2)",
        chapters: {
          list: "#list dd",
          item: {
            title: "a",
            link: "a"
          }
        }
      },
      chapterRule: {
        title: ".bookname h1",
        content: "#content"
      }
    };
    super(config);
  }
} 