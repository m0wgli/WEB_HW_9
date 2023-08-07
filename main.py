import json
import configparser
import scrapy

from itemadapter import ItemAdapter
from scrapy.item import Item, Field
from scrapy.crawler import CrawlerProcess
from models import Author, Quote
from mongoengine import *
from models import *


config = configparser.ConfigParser()

config.read("config.ini")

mongodb_url = config.get("DATABASE", "mongodb_url")
mongodb_uri = quote_plus(mongodb_url)  # Екрануємо спеціальні символи у URL


try:
    disconnect()  # Disconnect from any existing connections
    connect(db="hw_8", host=mongodb_url)
    print("Connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    raise


def load_authors(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        authors = json.load(file)
        for author_data in authors:
            author = Author(
                fullname=author_data["fullname"],
                date_born=author_data["date_born"],
                location_born=author_data["location_born"],
                bio=author_data["bio"],
            )
            author.save()
    print("Authors loaded successfully!")


def load_quotes(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        quotes = json.load(file)
        for quote_data in quotes:
            author_name = quote_data["author"]
            author = Author.objects(fullname=author_name).first()
            quote = Quote(
                tags=quote_data["tags"], author=author, text=quote_data["text"]
            )
            quote.save()
    print("Quotes loaded successfully!")


class QuoteItem(Item):
    text = Field()
    author = Field()
    tags = Field()


class AuthorItem(Item):
    fullname = Field()
    date_born = Field()
    location_born = Field()
    bio = Field()


class QuotesPipline:
    quotes = []
    authors = []

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if 'fullname' in adapter.keys():
            self.authors.append(dict(adapter))
        if 'text' in adapter.keys():
            self.quotes.append(dict(adapter))

    def close_spider(self, spider):
        with open("quotes.json", "w", encoding="utf-8") as fd:
            json.dump(self.quotes, fd, ensure_ascii=False, indent=2)
        with open("authors.json", "w", encoding="utf-8") as fd:
            json.dump(self.authors, fd, ensure_ascii=False, indent=2)


class QuotesSpider(scrapy.Spider):
    name = "to_scrapy"
    allowed_domains = ["quotes.toscrape.com"]
    start_urls = ["http://quotes.toscrape.com/"]
    custom_settings = {"ITEM_PIPELINES": {
        QuotesPipline: 300,
    }}

    def parse(self, response, **kwargs):
        for quote in response.xpath("/html//div[@class='quote']"):
            text = quote.xpath("span[@class='text']/text()").get().strip()
            author = quote.xpath("span/small[@class='author']/text()").get().strip()
            tags = quote.xpath("div[@class='tags']/a/text()").extract()
            yield QuoteItem(text=text, author=author, tags=tags)
            yield response.follow(url=self.start_urls[0] + quote.xpath('span/a/@href').get(),
                                  callback=self.parse_author)
        next_link = response.xpath('//li[@class="next"]/a/@href').get()
        if next_link:
            yield scrapy.Request(url=self.start_urls[0] + next_link)

    def parse_author(self, response, **kwargs):  # noqa
        content = response.xpath("/html//div[@class='author-details']")
        fullname = content.xpath('h3[@class="author-title"]/text()').get().strip()
        date_born = content.xpath('p/span[@class="author-born-date"]/text()').get().strip()
        location_born = content.xpath('p/span[@class="author-born-location"]/text()').get().strip()
        bio = content.xpath('div[@class="author-description"]/text()').get().strip()
        yield AuthorItem(fullname=fullname, date_born=date_born, location_born=location_born, bio=bio)


if __name__ == "__main__":
    load_authors('authors.json')
    load_quotes('quotes.json')
    process = CrawlerProcess()
    process.crawl(QuotesSpider)
    process.start()
    load_authors('authors.json')
    load_quotes('quotes.json')
