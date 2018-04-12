# -*- coding: utf-8 -*-
import json

import scrapy

from scrapy_zhihuuser.items import UserItem


class ZhihuSpider(scrapy.Spider):
    name = 'zhihu'
    allowed_domains = ['zhihu.com']
    start_urls = ['http://zhihu.com/']

    # 起始的大V账号
    start_user = 'excited-vczh'

    # 这里把查询的参数单独存储为user_query,user_url存储的为查询用户信息的url地址
    user_url = 'https://www.zhihu.com/api/v4/members/{user}?include={include}'
    user_query = 'allow_message,is_followed,is_following,is_org,is_blocking,employments,answer_count,follower_count,articles_count,gender,badge[?(type=best_answerer)].topics'

    # #follows_url存储的为关注列表的url地址,fllows_query存储的为查询参数。这里涉及到offset和limit是关于翻页的参数，0，20表示第一页
    follows_url = 'https://www.zhihu.com/api/v4/members/{user}/followers?include={include}&offset={offset}&limit={limit}'
    follows_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,badge[?(type=best_answerer)].topics'

    # #followers_url是获取粉丝列表信息的url地址，followers_query存储的为查询参数。
    followers_url = 'https://www.zhihu.com/api/v4/members/{user}/followees?include={include}&offset={offset}&limit={limit}'
    followers_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,badge[?(type=best_answerer)].topics'

    # 第一次访问的方法重写
    def start_requests(self):
        """
        这里重写了start_requests方法，分别请求了用户查询的url和关注列表的查询以及粉丝列表信息查询
        :return:
        """
        yield scrapy.Request(self.user_url.format(user=self.start_user, include=self.user_query),
                             callback=self.parse_user)
        yield scrapy.Request(
            self.follows_url.format(user=self.start_user, include=self.follows_query, offset=0, limit=20),
            callback=self.parse_follows)
        yield scrapy.Request(
            self.follows_url.format(user=self.start_user, include=self.followers_query, offset=0, limit=20),
            callback=self.parse_followers)

    def parse_user(self, response):
        """
        因为返回的是json格式的数据，所以这里直接通过json.loads获取结果
        :param response:
        :return:
        """
        result = json.loads(response.text)
        item = UserItem()
        # 这里循环判断获取的字段是否在自己定义的字段中，然后进行赋值
        for field in item.fields:
            if field in result.keys():
                item[field] = result.get(field)
        # 这里在返回item的同时返回Request请求，继续递归拿关注用户信息的用户获取他们的关注列表
        yield item
        yield scrapy.Request(
            self.follows_url.format(user=result.get("url_token"), include=self.follows_query, offset=0, limit=20),
            callback=self.parse_follows)
        yield scrapy.Request(
            self.followers_url.format(user=result.get("url_token"), include=self.followers_query, offset=0, limit=20),
            callback=self.parse_followers)

    def parse_follows(self, response):
        # 用户关注列表的解析，这里返回的也是json数据 这里有两个字段data和page，其中page是分页信息
        results = json.loads(response.text)
        if 'data' in results.keys():
            for result in results.get('data'):
                yield scrapy.Request(self.user_url.format(user=result.get('url_token'), include=self.user_query),
                                     self.parse_user)
        # 这里判断page是否存在并且判断page里的参数is_end判断是否为False，如果为False表示不是最后一页，否则则是最后一页
        if 'paging' in results.keys() and results.get('paging').get('is_end') == False:
            next_page = results.get('paging').get('next')
            # 获取下一页的地址然后通过yield继续返回Request请求，继续请求自己再次获取下页中的信息
            yield scrapy.Request(next_page, self.parse_follows)

    def parse_followers(self, response):
        """
        这里其实和关乎列表的处理方法是一样的
        用户粉丝列表的解析，这里返回的也是json数据 这里有两个字段data和page，其中page是分页信息
        :param response:
        :return:
        """

        results = json.loads(response.text)
        if 'data' in results.keys():
            for result in results.get('data'):
                yield scrapy.Request(self.user_url.format(user=result.get('url_token'), include=self.user_query),
                                     self.parse_user)
        if 'paging' in results.keys() and results.get('paging').get('is_end') == False:
            next_page = results.get('paging').get('next')
            yield scrapy.Request(next_page, self.parse_followers)
