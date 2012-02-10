#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from page import Page, Utils

class Plugins(object):

    def __init__(self):
        self._plugins = []

    def register(self, func):
        self._plugins.append((func.func_name, func))
        return func

    def __iter__(self):
        for name, plugin in self._plugins:
            yield plugin

    def __getitem__(self, key):
        return dict(self._plugins).get(key)

plugins = Plugins()

@plugins.register
def recent_posts():
    NUM = 5
    posts = Utils.lasted_list(NUM)
    html = '<h1>Recent Posts</h1>'
    for p in posts:
        html += '<a href="/page/%s">%s</a>' % (p.name, p.html_meta['title'])
    return '<div id="recent_posts">%s</div>' % html
'''
@plugins.register
def tags():
    alltags = Utils.get_tags()
    html = '<h1>Tags</h1>'
    for tag in alltags:
        html += '<a href="/tag/%s">%s</a>' % (tag['name'], tag['name'])
    return '<div id="tags">%s</div>' % html
'''
