#!/usr/bin/env python
import bottle
import urllib
import functools
import hashlib
from datetime import datetime
from page import Page, META, Validator, PageError, Utils, SessionMw
from bottle import mako_view as view, mako_template
from bottle import run, static_file, request, response, redirect, error
from plugins import plugins

app = bottle.Bottle()
need_login = functools.partial(Validator.need_login, req=request)
template = functools.partial(mako_template, plugins=plugins)

@app.get('/')
def index():
    pn = request.query.pn or 0
    skip = 10 * int(pn)
    page_list = Utils.lasted_list(10, skip)
    return template('index.html', page_list=page_list, pn=pn)

@app.get('/archives')
def archives():
    pn = request.query.pn or 0
    skip = 20 * int(pn)
    page_list = Utils.lasted_list(20, skip)
    pages = {}
    for page in page_list:
        year, day = page.html_meta['date'].strftime('%Y %b %d').split(' ', 1)
        if year not in pages:
            pages[year] = []
        pages[year].append((day, page))
    return template('archives.html', pages=pages, pn=pn)

@app.get('/page/<name>')
def page(name):
    p = Page(name)
    if p.html_exists:
        return template('page.html', page=p)
    else:
        raise bottle.HTTPError(404, 'Page not found')

@app.get('/<year:re:\d{4}>/<month:re:\d{2}>')
def archive(year, month):
    redirect('/')

@app.get('/tag/<name>')
def tag(name):
    page_list = Utils.tag_pages(5)
    return template('list.html', page_list=page_list)

@app.get('/tags')
def tags():
    pass

@app.get('/login')
@app.post('/login')
def login():
    if Validator.has_login(request):
        redirect('/')
    next = request.query.next or ''
    if request.method == 'POST':
        user = request.forms.username.strip()
        pwd  = request.forms.password.strip()
        if Validator.check_login(user, pwd):
            s = request.environ.get('beaker.session')
            s['user'] = hashlib.md5(user).hexdigest()
            url = next or '/admin'
            redirect(url)
    return template('login.html', next=next)

@app.get('/logout')
def logout():
    s = request.environ.get('beaker.session')
    if s and s.get('user'):
        del s['user']
    redirect('/')

@app.get('/admin')
@view('admin')
@need_login
def admin():
    pages = Utils.md_list()
    return {'pages': pages}

@app.get('/admin/new')
@app.post('/admin/new')
@need_login
def admin_new():
    if request.method == 'POST':
        name = request.forms.name.lower().strip()
        try:
            Validator.check_name(name)
            name = urllib.quote_plus(name)
            d = datetime.now()
            name = d.strftime('%Y-%m-%d-') + name
            p = Page(name)
            p.new(d)
            redirect('/admin/edit/%s' % name)
        except PageError, e:
            return template('admin_new', msg=str(e))
    else:
        return template('admin_new')

@app.get('/admin/edit/<name>')
@need_login
def admin_edit(name):
    try:
        Validator.check_name(name)
        p = Page(name)
        return template('admin_edit', page=p)
    except PageError, e:
        pass

#AJAX
@app.post('/admin/ajax/<action>')
@need_login
def admin_ajax(action):
    name = request.forms.name
    try:
        Validator.check_name(name)
        p = Page(name)
        if action == 'save':
            p.content = request.forms.content
            p.save()
        elif action == 'publish':
            p.publish()
        elif action == 'remove':
            delall = bool(request.forms.delall)
            p.remove(delall)
        else:
            raise PageError('No such action')
    except PageError, e:
        return {'status': 'fail', 'data': str(e)}
    return {'status': 'ok', 'data': ''}


@app.get('/static/<filename:re:.+\.(css|js)>')
def static(filename):
    return static_file(filename, root='./static/')

@error(404)
def error_404():
    return "404"

application = SessionMw(app)

if __name__ == '__main__':
    #bottle.debug(True)
    '''from gevent import monkey
    monkey.patch_all()
    run(app, host='localhost', port=8000, server='gevent', reloader=True)'''
    run(app, host='localhost', port=8000, reloader=True)
