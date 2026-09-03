import asyncio
import aiosqlite
import json
import aiohttp_jinja2
import jinja2
import base64
from aiohttp import web
from os import environ
from ftp.server import User, Permission
import json

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
    db_type = request.app['db_type']
    users = []
    if db_type == "mongodb":
        users_cursor = db.users.find({})
        async for u in users_cursor:
            users.append(u)
    else:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM users") as cursor:
                for row in await cursor.fetchall():
                    d = dict(row)
                    d["permissions"] = json.loads(d.get("permissions", "[]"))
                    users.append(d)
    return aiohttp_jinja2.render_template('index.html', request, {'users': users})

async def handle_add_user(request):
    if request.method == 'POST':
        data = await request.post()
        login = data.get('login')
        password = data.get('password')
        if login and password:
            db = request.app['db']
            db_type = request.app['db_type']
            if db_type == "mongodb":
                existing = await db.users.find_one({"login": login})
                if not existing:
                    await db.users.insert_one({"login": login, "password": password, "permissions": []})
            else:
                async with aiosqlite.connect(db) as conn:
                    async with conn.execute("SELECT id FROM users WHERE login = ?", (login,)) as cursor:
                        existing = await cursor.fetchone()
                    if not existing:
                        default_perms = json.dumps([{"path": "/", "readable": True, "writable": True}])
                        await conn.execute("INSERT INTO users (login, password, permissions) VALUES (?, ?, ?)", (login, password, default_perms))
                        await conn.commit()
        raise web.HTTPFound('/')
    return aiohttp_jinja2.render_template('add_user.html', request, {})

async def handle_edit_user(request):
    login = request.match_info['login']
    db = request.app['db']
    db_type = request.app['db_type']

    if db_type == "mongodb":
        user_doc = await db.users.find_one({"login": login})
    else:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM users WHERE login = ?", (login,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_doc = dict(row)
                    user_doc["permissions"] = json.loads(user_doc.get("permissions", "[]"))
                else:
                    user_doc = None

    if not user_doc:
        raise web.HTTPNotFound()

    if request.method == 'POST':
        data = await request.post()
        action = data.get('action')

        if db_type == "mongodb":
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
        else:
            async with aiosqlite.connect(db) as conn:
                if action == 'add_perm':
                    path = data.get('path', '/').strip()
                    if not path.startswith('/'): path = '/' + path
                    readable = data.get('readable') == 'on'
                    writable = data.get('writable') == 'on'
                    new_perm = {"path": path, "readable": readable, "writable": writable}
                    user_doc["permissions"].append(new_perm)
                    await conn.execute("UPDATE users SET permissions = ? WHERE login = ?", (json.dumps(user_doc["permissions"]), login))
                    await conn.commit()
                elif action == 'del_perm':
                    path = data.get('path')
                    if path:
                        user_doc["permissions"] = [p for p in user_doc["permissions"] if p["path"] != path]
                        await conn.execute("UPDATE users SET permissions = ? WHERE login = ?", (json.dumps(user_doc["permissions"]), login))
                        await conn.commit()
                elif action == 'change_pass':
                    new_pass = data.get('password')
                    if new_pass:
                        await conn.execute("UPDATE users SET password = ? WHERE login = ?", (new_pass, login))
                        await conn.commit()
        raise web.HTTPFound(f'/edit/{login}')

    # Reload after potential modifications
    if db_type == "mongodb":
        user_doc = await db.users.find_one({"login": login})
    else:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM users WHERE login = ?", (login,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_doc = dict(row)
                    user_doc["permissions"] = json.loads(user_doc.get("permissions", "[]"))
                else:
                    user_doc = None

    return aiohttp_jinja2.render_template('edit_user.html', request, {'user': user_doc})

async def handle_delete_user(request):
    login = request.match_info['login']
    db = request.app['db']
    db_type = request.app['db_type']

    if request.method == 'POST':
        if db_type == "mongodb":
            await db.users.delete_one({"login": login})
        else:
            async with aiosqlite.connect(db) as conn:
                await conn.execute("DELETE FROM users WHERE login = ?", (login,))
                await conn.commit()
        raise web.HTTPFound('/')

    raise web.HTTPMethodNotAllowed('POST', ['POST'])

async def start_web_server(db, port=8080, db_type="mongodb"):
    app = web.Application(middlewares=[basic_auth_middleware])
    app['db'] = db
    app['db_type'] = db_type
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
