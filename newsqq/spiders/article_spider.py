# -*- coding: utf-8 -*-
import scrapy
import pymongo
from newsqq.items import NewsqqItem


class ArticleSpiderSpider(scrapy.Spider):
    name = 'article_spider'

    def __init__(self):
        self.client = pymongo.MongoClient('localhost', 27017)
        self.newsQQDB = self.client['newsQQDB']
        self.links = self.newsQQDB['links']
        self.article = self.newsQQDB['article']
        print('正在更新数据库...')
        for i in self.links.find():  # 更新数据库，将http链接转为https
            new_href = "https:" + i['href'].split(':')[1]
            self.links.update_one({'href': i['href']}, {'$set': {'href': new_href}})
        print('更新完成')
        links_array = [i['href'] for i in self.links.find()]
        article_array = [i['href'] for i in self.article.find()]
        x = set(links_array)
        y = set(article_array)
        print('总共需获取' + str(len(x)), '已获取' + str(len(y)))
        left_set = x.difference(y)
        self.myLinks = list(left_set)
        self.myNum = 0
        self.myLimit = len(left_set)
        print('此次需要获取的正文数为' + str(self.myLimit) + '，开始获取链接正文...')

        self.allowed_domains = ['new.qq.com']
        s_url = self.myLinks[0]
        # s_url = 'https://new.qq.com/omn/20181230/20181230A0OZJD00'  #未解决难题
        # s_url = 'https://new.qq.com/omn/20190101/20190101B0C68V.html'  # 已适配
        self.start_urls = [s_url]

    def parse(self, response):
        news = NewsqqItem()
        article_array = []
        second_article = []
        print(response.request.headers['User-Agent'])
        p_list = response.xpath("//p[1]//parent::div/p")
        print(response.text)
        for p in p_list:
            p_str = p.xpath("string(.)").extract_first()  # 将./text()换为string(.)，返回当前元素的所有节点文本内容
            p_text = p.xpath("./text()").extract_first()  # 新增
            if p_str:
                article_array.append(p_str)

            # 新增内容
            if p.xpath(".//img"):  # 有照片
                img_href = 'https:' + p.xpath(".//img/@src").extract_first()
                content = {
                    'type': 1,
                    'value': img_href
                }
                second_article.append(content)
                img_desc = ''
                if p.xpath(".//i[@class='desc']"):  # 有照片描述
                    img_desc =p.xpath(".//i[@class='desc']/text()").extract_first()
                    content = {
                        'type': 2,
                        'value': img_desc
                    }
                    second_article.append(content)
            elif p.xpath("./strong") and not p_text:    # 整段均为强调
                strong_text = p.xpath("./strong/text()").extract_first()
                content = {
                    'type': 3,
                    'value': strong_text
                }
                second_article.append(content)
            elif p_text:
                content = {
                    'type': 0,
                    'value': p_str  # 不能为p_text，否则不能获取到有强调的段落
                }
                second_article.append(content)
            ######

        article_str = '\n'.join(article_array)
        news['article'] = article_str
        news['href'] = response.request.url
        news['second_article'] = second_article
        yield news
        self.myNum += 1

        if self.myNum < self.myLimit:
            print(self.myNum)
            next_link = self.myLinks[self.myNum]
            print(next_link)
            yield scrapy.Request(next_link, callback=self.parse)
