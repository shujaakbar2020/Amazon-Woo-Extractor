#!/usr/bin/venv python3
import tkinter as tk

import scrapy
import scrapy.crawler as crawler
from multiprocessing import Process, Queue
from twisted.internet import reactor
from urllib.parse import urlencode
from urllib.parse import urljoin
import re
import json

from woocommerce import API

# WooCommerce REST API Integration
wcapi = API(
    url="https://blush-blooms.com",
    consumer_key="ck_c0038260d0685cc16fa1500434798e0b8f2e1879",
    consumer_secret="cs_3da9a061dc038b77781d1023bf429ded37fddd0f",
    # verify_ssl = False,
    wp_api=True,
    version="wc/v3",
    query_string_auth=True,
    timeout=20
)

# queries = ["Women's Formal Dresses"]  # Enter keywords here ['keyword1', 'keyword2', 'etc']
queries = []
key = "dfa04ec7c7266d00782266aad5772a76"
global ids
# Insert Scraperapi API key here. Signup here for free trial with 5,000 requests: https://www.scraperapi.com/signup
# key = "c3be530c8479d2fe712cef4393a2a42a"


def set_ids(id):
    global ids
    ids = id


def get_ids():
    return ids


def set_queries():
    # queries.append(str(amazon_query.get()))
    pass


def get_url(url):
    payload = {'api_key': key, 'url': url, 'country_code': 'us'}
    proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    return proxy_url


def get_number():
    if no_of_products.get() is None:
        return None
    else:
        return int(no_of_products.get())


class AmazonSpider(scrapy.Spider):
    name = 'amazon'

    def start_requests(self):
        # queries[0] = amazon_query.get()
        # set_queries()
        for query in queries:
            url = 'https://www.amazon.com/s?' + urlencode({'k': query})
            # url = 'https://www.amazon.comMen’s Wallets/NZXT-H510i-Mid-Tower-Integrated-Water-Cooling/dp/B07TC73F72/ref
            # =sr_1_1_sspa?dchild=1&keywords=GPU&qid=1607272047&sr=8-1-spons&psc=1&spLa
            # =ZW5jcnlwdGVkUXVhbGlmaWVyPUEySVVYSlYxRkg3TUhHJmVuY3J5cHRlZElkPUEwODAyNzIwSVpDNjdXWkVYRUtLJmVuY3J5cHRlZEFkSWQ9QTA4OTkyNTIyNUJTUzNXMDU0WlpZJndpZGdldE5hbWU9c3BfYXRmJmFjdGlvbj1jbGlja1JlZGlyZWN0JmRvTm90TG9nQ2xpY2s9dHJ1ZQ=='
            yield scrapy.Request(url=get_url(url), callback=self.parse_keyword_response)

    def parse_keyword_response(self, response):
        products = response.xpath('//*[@data-asin]')
        num = get_number()
        if num is None:
            for product in products:
                asin = product.xpath('@data-asin').extract_first()
                product_url = f"https://www.amazon.com/dp/{asin}"
                yield scrapy.Request(url=get_url(product_url), callback=self.parse_product_page, meta={'asin': asin})

                next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()
            if next_page:
                url = urljoin("https://www.amazon.com", next_page)
                yield scrapy.Request(url=get_url(url), callback=self.parse_keyword_response)
        elif num is not None:
            var = 0
            while var < num:
                print(var)
                try:
                    product = products[var]
                except:
                    var = num + 1
                print(products)
                asin = product.xpath('@data-asin').extract_first()
                product_url = f"https://www.amazon.com/dp/{asin}"
                var += 1
                yield scrapy.Request(url=get_url(product_url), callback=self.parse_product_page, meta={'asin': asin})

                next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()
            if next_page:
                url = urljoin("https://www.amazon.com", next_page)
                yield scrapy.Request(url=get_url(url), callback=self.parse_keyword_response)

    def parse_product_page(self, response):
        weight = 0
        height = 0
        width = 0
        length = 0
        asin = response.meta['asin']

        # // *[ @ id = "productDescription_feature_div"] / h2
        title = response.xpath('//*[@id="productTitle"]/text()').extract_first()
        desc = response.xpath('//*[@id="productDescription"]/p/text()').extract_first()
        dim = response.xpath('//*[@id="detailBullets_feature_div"]/ul/li[1]/span/span[2]/text()').extract_first()
        try:
            first = dim.split(';')
            len_wid_h = first[0].split()
            height = str(len_wid_h[0])
            length = str(len_wid_h[2])
            width = str(len_wid_h[4])
            weight_lbs = first[1].split()
            if weight_lbs[1] == "Ounces":
                weight = str(round(float(weight_lbs[0]) / 16, 2))
            else:
                weight = weight_lbs[0]
        except:
            height = ""
            length = ""
            width = ""
            weight = ""

        image = re.search('"large":"(.*?)"', response.text).groups()[0]
        rating = response.xpath('//*[@id="acrPopover"]/@title').extract_first()
        number_of_reviews = response.xpath('//*[@id="acrCustomerReviewText"]/text()').extract_first()
        price = response.xpath('//*[@id="priceblock_ourprice"]/text()').extract_first()

        if not price:
            price = response.xpath('//*[@data-asin-price]/@data-asin-price').extract_first() or \
                    response.xpath('//*[@id="price_inside_buybox"]/text()').extract_first()

        regular_price = price.split('-')

        temp = response.xpath('//*[@id="twister"]')
        sizes = []
        colors = []
        if temp:
            s = re.search('"variationValues" : ({.*})', response.text).groups()[0]
            json_acceptable = s.replace("'", "\"")
            di = json.loads(json_acceptable)
            sizes = di.get('size_name', [])
            colors = di.get('color_name', [])

        bullet_points = response.xpath('//*[@id="feature-bullets"]//li/span/text()').extract()
        seller_rank = response.xpath(
            '//*[text()="Amazon Best Sellers Rank:"]/parent::*//text()[not(parent::style)]').extract()

        data = {'sku': asin, 'name': title, 'type': 'simple', 'regular_price': regular_price[0], 'Description': desc,
                'short_description': '',
                'images': [{'src': image}], 'categories': [{'id': get_ids()}],
                'dimensions': {'length': length, 'width': width, 'height': height}, 'weight': weight}
        wcapi.post("products", data)

        yield {'name': title, 'type': 'simple', 'regular_price': regular_price[0], 'Description': desc,
               'short_description': '',
               'images': [{'src': image}], 'categories': [{'id': get_ids()}],
               'Dimensions': {'length': length, 'width': width, 'height': height}, 'weight': weight}


'''

process = CrawlerProcess()
process.crawl(AmazonSpider)
process.start()
'''


def show_entry_fields():
    # print(e1.get())
    # process = CrawlerProcess()
    # process.crawl(AmazonSpider)
    # process.start()
    pass


def run_spider(spider):
    def f(q):
        try:
            runner = crawler.CrawlerRunner()
            deferred = runner.crawl(spider)
            deferred.addBoth(lambda _: reactor.stop())
            reactor.run()
            q.put(None)
        except Exception as e:
            q.put(e)

    q = Queue()
    p = Process(target=f, args=(q,))
    p.start()
    result = q.get()
    p.join()

    if result is not None:
        raise result


def start_func():
    set_ids(int(category_id.get()))
    queries.append(str(amazon_query.get()))
    run_spider(AmazonSpider)
    queries.pop()


master = tk.Tk(className="Add Products")
master.geometry("300x230")

tk.Label(master, text="").grid(row=0)
tk.Label(master, text="Amazon Query:").grid(row=1)
tk.Label(master, text="").grid(row=2)
tk.Label(master, text="No. of Products:").grid(row=3)
tk.Label(master, text="").grid(row=4)
tk.Label(master, text="Category ID:").grid(row=5)
tk.Label(master, text="").grid(row=6)
# tk.Label(master, text="Category ID:").grid(row=3)

amazon_query = tk.Entry(master)
no_of_products = tk.Entry(master)
category_id = tk.Entry(master)
# e4 = tk.Entry(master)

amazon_query.grid(row=1, column=1)
no_of_products.grid(row=3, column=1)
category_id.grid(row=5, column=1)
# e4.grid(row=3, column=1)

tk.Button(master, text='Quit', command=master.quit).grid(row=7, column=0, sticky=tk.W, pady=4)
tk.Button(master, text='Add Products', command=start_func).grid(row=7, column=1, sticky=tk.W, pady=4)

tk.mainloop()
