#!/usr/bin/env python
import os
import re
import codecs
import markdown
import string
import pymongo
import functools
import hashlib
from datetime import datetime
from beaker.middleware import SessionMiddleware
from bottle import redirect

class PageError(Exception): pass

PAGEDIR  = os.path.abspath('./pages')
HTMLDIR  = os.path.abspath('./htmls')
CACHEDIR = os.path.abspath('./cache')
ENCODING = 'UTF-8'

session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 1800,
    'session.data_dir': CACHEDIR,
    'session.auto': True
}
SessionMw = functools.partial(SessionMiddleware, config=session_opts)

META = u'''\
!--
author: {author}
title: {title}
date: {date}
tags: {tags}
--!'''
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

conn = pymongo.Connection('localhost', 27017)
db   = conn.blog

class Page(object):
    pagedir = PAGEDIR
    htmldir = HTMLDIR
    options = ['codehilite']
    def __init__(self, name, meta=None):
        if os.path.sep in name:
            raise PageError('Invalid page name: %s' % name)
        self.name     = name
        self.pagename = os.path.join(self.pagedir, name+'.md')
        self.htmlname = os.path.join(self.htmldir, name+'.html')
        self._content = None
        self._html    = None
        self._meta    = meta
    
    @property
    def exists(self):
        return os.path.exists(self.pagename)

    @property
    def html_exists(self):
        return os.path.exists(self.htmlname)

    @property
    def mdfile(self):
        if not self.exists:
            raise PageError('Markdown page %s not exists' % self.name)
        return codecs.open(self.pagename, encoding=ENCODING)

    @property
    def htmlfile(self):
        if not self.html_exists:
            raise PageError('HTML page %s not exists' % self.name)
        return codecs.open(self.htmlname, encoding=ENCODING)
    
    @property
    def content(self):
        if not self._content:
            self._content = self.mdfile.read()
        return self._content
    @content.setter
    def content(self, value):
        self._content = value

    def _parse_meta(self, meta_str):
        meta = {}
        for item in meta_str.strip().splitlines():
            k, v = [one.strip() for one in item.split(':', 1)]
            meta[k] = v
        return meta

    @property
    def md(self):
        content = self.content.split(os.linesep*2, 1)
        meta = content[0].strip()
        m = re.match(r'^!--(.*?)--!$', meta, re.S)
        if m:
            meta = self._parse_meta(m.group(1))
        else:
            raise PageError('Invalid meta data in Markdown page %s' % self.name)
        body = content[1] if len(content) == 2 else ''
        return meta, body

    @property
    def html(self):
        if not self._html:
            self._html = self.htmlfile.read()
        return self._html or ''

    @property
    def summary(self):
        m = re.search(r'<p[^>]*>(.+?)</p>', self.html, re.S)
        return m.group(1).strip() if m else ''

    @property
    def html_meta(self):
        if not self._meta:
            self._meta = db.posts.find_one({'name': self.name})
        return self._meta or {}

    def _write_md(self, content):
        with open(self.pagename, 'w') as f:
            f.write(content.encode(ENCODING))

    def _write_html(self, body):
        with open(self.htmlname, 'w') as f:
            f.write(body.encode(ENCODING))

    def _write_mongo(self, meta):
        meta['name'] = self.name
        meta['date'] = datetime.strptime(meta['date'], TIME_FORMAT)
        meta['tags'] = [tag.strip() for tag in meta['tags'].split(',')]
        if db.posts.find({'name': self.name}).count():
            db.posts.update({'name': self.name}, \
                {'$set': {'date': meta['date'], 'tags': meta['tags']}})
        else:
            db.posts.insert(meta)
    
    def _new(self, d=None):
        if d is None: 
            d = datetime.now()
        meta = META.format(author = 'Changxi Yu', 
                           title  = self.name.title(),
                           date   = d.strftime(TIME_FORMAT),
                           tags   = '')
        body = 'Write markdown content here'
        content = meta + os.linesep*2 + body
        self._write_md(content)

    def new(self, date=None):
        if self.exists:
            raise PageError('Page has been existed')
        else:
            self._new(date)
    
    @property
    def need_publish(self):
        return not self.html_exists or \
            os.path.getmtime(self.pagename) > os.path.getmtime(self.htmlname) \
            if self.exists else False

    def publish(self):
        if self.need_publish:
            meta, body = self.md
            html = markdown.markdown(body, self.options)
            self._write_mongo(meta)
            self._write_html(html)

    def save(self):
        self._write_md(self.content)

    def _delhtml(self):
        os.unlink(self.htmlname)
        db.posts.remove({'name': self.name})

    def remove(self, delall=0):
        if delall:
            os.unlink(self.pagename)
        self._delhtml()

class Utils(object):

    @staticmethod
    def lasted_list(num, skip=0):
        cur = db.posts.find()
        for meta in cur.sort('date', pymongo.DESCENDING).limit(num).skip(skip):
            yield Page(meta['name'], meta)
    
    @staticmethod
    def tag_pages(tag):
        cur = db.posts.find()
        for meta in cur.sort('date', pymongo.DESCENDING):
            if tag in meta['tags']:
                yield Page(meta['name'], meta)
    
    @staticmethod
    def md_list():
        mds = os.listdir(PAGEDIR)
        mds.sort(reverse=True)
        if mds:
            for name in mds:
                name = name[:-3]
                yield Page(name)

USERNAME = '900150983cd24fb0d6963f7d28e17f72'
PASSWORD = 'e10adc3949ba59abbe56e057f20f883e'

class Validator(object):
    
    @staticmethod
    def check_login(username, password):
        return hashlib.md5(username).hexdigest() == USERNAME and \
               hashlib.md5(password).hexdigest() == PASSWORD

    @staticmethod
    def has_login(req):
        s = req.environ.get('beaker.session')
        if s and s.get('user') == USERNAME:
            return True
        else:
            return False

    @staticmethod
    def need_login(func, req=None):
        def wraper(*args, **kargs):
            if Validator.has_login(req):
                return func(*args, **kargs)
            else:
                redirect('/login?next=%s' % req.path)
        return wraper
    
    @staticmethod
    def check_name(name):
        if not name: raise PageError('Page name can not be empty')
        name_chars = string.lowercase + string.digits + '+-_ '
        for c in name.lower():
            if c not in name_chars:
                raise PageError('Invalid char in page name')

