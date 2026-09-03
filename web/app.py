import asyncio
import aiohttp_jinja2
import jinja2
import base64
from aiohttp import web
from os import environ
from ftp.server import User, Permission

# Basic Auth wrapper
@web.middleware
async def basic_auth_middleware(request, handler):
    auth_header = request.headers.get('Authorization')
    expected_password = environ.get('WEB_ADMIN_PASSWORD')

    if not expected_password:
        return await handler(request)

    if auth_header and auth_header.startswith('Basic '):
        encoded = auth_header[6:]
        try:
            decoded = base64.b64decode(encoded).decode('utf-8')
            username, password = decoded.split(':', 1)
            # We don't care about the username, just the password for simple admin access
            if password == expected_password:
                return await handler(request)
        except Exception:
            pass

    return web.Response(
        status=401,
        headers={'WWW-Authenticate': 'Basic realm="Nebula FTP Admin"'},
        text='Unauthorized'
    )

async def handle_index(request):
    db = request.app['db']
    users_cursor = db.users.find({})
    users = []
    async for u in users_cursor:
        users.append(u)
    return aiohttp_jinja2.render_template('index.html', request, {'users': users})

async def handle_add_user(request):
    if request.method == 'POST':
        data = await request.post()
        login = data.get('login')
        password = data.get('password')
        if login and password:
            db = request.app['db']
            existing = await db.users.find_one({"login": login})
            if not existing:
                await db.users.insert_one({"login": login, "password": password, "permissions": []})
        raise web.HTTPFound('/')
    return aiohttp_jinja2.render_template('add_user.html', request, {})

async def handle_edit_user(request):
    login = request.match_info['login']
    db = request.app['db']
    user_doc = await db.users.find_one({"login": login})
    if not user_doc:
        raise web.HTTPNotFound()

    if request.method == 'POST':
        data = await request.post()
        action = data.get('action')
        if action == 'add_perm':
            path = data.get('path', '/').strip()
            if not path.startswith('/'): path = '/' + path
            readable = data.get('readable') == 'on'
            writable = data.get('writable') == 'on'
            await db.users.update_one({"login": login}, {"$push": {"permissions": {"path": path, "readable": readable, "writable": writable}}})
        elif action == 'del_perm':
            path = data.get('path')
            await db.users.update_one({"login": login}, {"$pull": {"permissions": {"path": path}}})
        elif action == 'change_pass':
            new_pass = data.get('password')
            if new_pass:
                await db.users.update_one({"login": login}, {"$set": {"password": new_pass}})
        raise web.HTTPFound(f'/edit/{login}')

    # Reload after potential modifications
    user_doc = await db.users.find_one({"login": login})
    return aiohttp_jinja2.render_template('edit_user.html', request, {'user': user_doc})

async def handle_delete_user(request):
    login = request.match_info['login']
    db = request.app['db']

    if request.method == 'POST':
        await db.users.delete_one({"login": login})
        raise web.HTTPFound('/')

    raise web.HTTPMethodNotAllowed('POST', ['POST'])

async def start_web_server(db, port=8080):
    app = web.Application(middlewares=[basic_auth_middleware])
    app['db'] = db
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('web/templates'))

    app.router.add_get('/', handle_index)
    app.router.add_get('/add', handle_add_user)
    app.router.add_post('/add', handle_add_user)
    app.router.add_get('/edit/{login}', handle_edit_user)
    app.router.add_post('/edit/{login}', handle_edit_user)
    app.router.add_post('/delete/{login}', handle_delete_user)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    return runner
