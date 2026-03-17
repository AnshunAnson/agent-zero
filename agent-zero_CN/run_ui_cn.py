#!/usr/bin/env python3
"""
Agent Zero 中文版启动脚本
- 引用原项目源码 (E:\Agent\agent-zero)
- 覆盖静态文件服务，支持 usr/webui/ 中文组件
"""

import sys
import os

# 添加原项目路径
ORIGINAL_PROJECT = r"E:\Agent\agent-zero"
sys.path.insert(0, ORIGINAL_PROJECT)

# 切换工作目录到原项目（确保相对路径正确）
os.chdir(ORIGINAL_PROJECT)

# ============ 以下代码复制自 run_ui.py，添加 usr/webui 覆盖逻辑 ============

from datetime import timedelta
import secrets
import time
import socket
import struct
from functools import wraps
import threading
import asyncio

import urllib.request
import urllib.error
import uvicorn
from flask import Flask, request, Response, session, redirect, url_for, render_template_string, send_file
from werkzeug.wrappers.response import Response as BaseResponse
from werkzeug.wrappers.request import Request as WerkzeugRequest

import initialize
from python.helpers import files, git, mcp_server, fasta2a_server, settings as settings_helper
from python.helpers.files import get_abs_path
from python.helpers import runtime, dotenv, process
from python.helpers.websocket import WebSocketHandler, validate_ws_origin
from python.helpers.extract_tools import load_classes_from_folder
from python.helpers.api import ApiHandler
from python.helpers.print_style import PrintStyle
from python.helpers import login
import socketio
from socketio import ASGIApp, packet
from starlette.applications import Starlette
from starlette.routing import Mount
from uvicorn.middleware.wsgi import WSGIMiddleware
from python.helpers.websocket_manager import WebSocketManager
from python.helpers.websocket_namespace_discovery import discover_websocket_namespaces

import logging
logging.getLogger().setLevel(logging.WARNING)

os.environ["TZ"] = "UTC"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
if hasattr(time, 'tzset'):
    time.tzset()

# ============ 中文版：定义 usr/webui 覆盖路径 ============
_CN_WEBUI_PATH = r"E:\Agent\agent-zero_me\usr\webui"
_DEFAULT_WEBUI_PATH = get_abs_path("./webui")

def _find_static_file(filename: str) -> str | None:
    """查找静态文件，优先使用中文版 usr/webui/"""
    # 处理 usr/webui/ 前缀 - 去掉前缀后查找
    if filename.startswith("usr/webui/"):
        filename = filename[len("usr/webui/"):]
    
    # 先检查中文版
    cn_path = os.path.join(_CN_WEBUI_PATH, filename)
    if os.path.isfile(cn_path):
        return cn_path
    # 再检查默认 webui/
    default_path = os.path.join(_DEFAULT_WEBUI_PATH, filename)
    if os.path.isfile(default_path):
        return default_path
    return None

# 初始化 Flask - 禁用默认静态文件处理，使用自定义路由
webapp = Flask("app", static_folder=None, static_url_path="/")
webapp.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

UPLOAD_LIMIT_BYTES = 5 * 1024 * 1024 * 1024
WerkzeugRequest.max_form_memory_size = UPLOAD_LIMIT_BYTES

webapp.config.update(
    JSON_SORT_KEYS=False,
    SESSION_COOKIE_NAME="session_" + runtime.get_runtime_id(),
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    MAX_CONTENT_LENGTH=int(os.getenv("FLASK_MAX_CONTENT_LENGTH", str(UPLOAD_LIMIT_BYTES))),
    MAX_FORM_MEMORY_SIZE=int(os.getenv("FLASK_MAX_FORM_MEMORY_SIZE", str(UPLOAD_LIMIT_BYTES))),
)

lock = threading.RLock()

socketio_server = socketio.AsyncServer(
    async_mode="asgi",
    namespaces="*",
    cors_allowed_origins=lambda _origin, environ: validate_ws_origin(environ)[0],
    logger=False,
    engineio_logger=False,
    ping_interval=25,
    ping_timeout=20,
    max_http_buffer_size=50 * 1024 * 1024,
)

websocket_manager = WebSocketManager(socketio_server, lock)
_settings = settings_helper.get_settings()
settings_helper.set_runtime_settings_snapshot(_settings)
websocket_manager.set_server_restart_broadcast(
    _settings.get("websocket_server_restart_enabled", True)
)


def is_loopback_address(address):
    loopback_checker = {
        socket.AF_INET: lambda x: (
            struct.unpack("!I", socket.inet_aton(x))[0] >> (32 - 8)
        ) == 127,
        socket.AF_INET6: lambda x: x == "::1",
    }
    address_type = "hostname"
    try:
        socket.inet_pton(socket.AF_INET6, address)
        address_type = "ipv6"
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET, address)
            address_type = "ipv4"
        except socket.error:
            address_type = "hostname"

    if address_type == "ipv4":
        return loopback_checker[socket.AF_INET](address)
    elif address_type == "ipv6":
        return loopback_checker[socket.AF_INET6](address)
    else:
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                r = socket.getaddrinfo(address, None, family, socket.SOCK_STREAM)
            except socket.gaierror:
                return False
            for family, _, _, _, sockaddr in r:
                if not loopback_checker[family](sockaddr[0]):
                    return False
        return True


def requires_api_key(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        from python.helpers.settings import get_settings
        valid_api_key = get_settings()["mcp_server_token"]

        if api_key := request.headers.get("X-API-KEY"):
            if api_key != valid_api_key:
                return Response("Invalid API key", 401)
        elif request.json and request.json.get("api_key"):
            api_key = request.json.get("api_key")
            if api_key != valid_api_key:
                return Response("Invalid API key", 401)
        else:
            return Response("API key required", 401)
        return await f(*args, **kwargs)

    return decorated


def requires_loopback(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        if not is_loopback_address(request.remote_addr):
            return Response("Access denied.", 403, {})
        return await f(*args, **kwargs)
    return decorated


def requires_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        user_pass_hash = login.get_credentials_hash()
        if not user_pass_hash:
            return await f(*args, **kwargs)
        if session.get('authentication') != user_pass_hash:
            return redirect(url_for('login_handler'))
        return await f(*args, **kwargs)
    return decorated


def csrf_protect(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        token = session.get("csrf_token")
        header = request.headers.get("X-CSRF-Token")
        cookie = request.cookies.get("csrf_token_" + runtime.get_runtime_id())
        sent = header or cookie
        if not token or not sent or token != sent:
            return Response("CSRF token missing or invalid", 403)
        return await f(*args, **kwargs)
    return decorated


# ============ 中文版：静态文件覆盖路由 ============
@webapp.route("/<path:filename>", methods=["GET"])
@requires_auth
async def serve_static_with_override(filename: str):
    """提供静态文件，支持中文版 usr/webui/ 覆盖"""
    file_path = _find_static_file(filename)
    if file_path:
        return send_file(file_path)
    return Response("Not found", 404)


@webapp.route("/login", methods=["GET", "POST"])
async def login_handler():
    error = None
    if request.method == 'POST':
        user = dotenv.get_dotenv_value("AUTH_LOGIN")
        password = dotenv.get_dotenv_value("AUTH_PASSWORD")
        if request.form['username'] == user and request.form['password'] == password:
            session['authentication'] = login.get_credentials_hash()
            return redirect(url_for('serve_index'))
        else:
            await asyncio.sleep(1)
            error = 'Invalid Credentials. Please try again.'
    login_page_content = files.read_file("webui/login.html")
    return render_template_string(login_page_content, error=error)


@webapp.route("/logout")
async def logout_handler():
    session.pop('authentication', None)
    return redirect(url_for('login_handler'))


@webapp.route("/", methods=["GET"])
@requires_auth
async def serve_index():
    gitinfo = None
    try:
        gitinfo = git.get_git_info()
    except Exception:
        gitinfo = {"version": "unknown", "commit_time": "unknown"}
    # 优先读取中文版 index.html
    cn_index_path = os.path.join(_CN_WEBUI_PATH, "index.html")
    if os.path.isfile(cn_index_path):
        with open(cn_index_path, "r", encoding="utf-8") as f:
            index = f.read()
    else:
        index = files.read_file("webui/index.html")
    index = files.replace_placeholders_text(
        _content=index,
        version_no=gitinfo["version"],
        version_time=gitinfo["commit_time"],
        runtime_id=runtime.get_runtime_id(),
        runtime_is_development=("true" if runtime.is_development() else "false"),
        logged_in=("true" if login.get_credentials_hash() else "false"),
    )
    return index


def _build_websocket_handlers_by_namespace(socketio_server, lock):
    discoveries = discover_websocket_namespaces(
        handlers_folder="python/websocket_handlers",
        include_root_default=True,
    )
    handlers_by_namespace = {}
    for discovery in discoveries:
        namespace = discovery.namespace
        for handler_cls in discovery.handler_classes:
            handler = handler_cls.get_instance(socketio_server, lock)
            handlers_by_namespace.setdefault(namespace, []).append(handler)
    return handlers_by_namespace


def configure_websocket_namespaces(*, webapp, socketio_server, websocket_manager, handlers_by_namespace):
    namespace_map = {namespace: list(handlers) for namespace, handlers in handlers_by_namespace.items()}
    namespace_map.setdefault("/", [])
    websocket_manager.register_handlers(namespace_map)
    allowed_namespaces = set(namespace_map.keys())
    original_handle_connect = socketio_server._handle_connect

    async def _handle_connect_with_namespace_gatekeeper(eio_sid, namespace, data):
        requested = namespace or "/"
        if requested not in allowed_namespaces:
            await socketio_server._send_packet(
                eio_sid,
                socketio_server.packet_class(
                    packet.CONNECT_ERROR,
                    data={"message": "UNKNOWN_NAMESPACE", "data": {"code": "UNKNOWN_NAMESPACE", "namespace": requested}},
                    namespace=requested,
                ),
            )
            return
        await original_handle_connect(eio_sid, namespace, data)

    socketio_server._handle_connect = _handle_connect_with_namespace_gatekeeper

    def _register_namespace_handlers(namespace, namespace_handlers):
        auth_required = False
        csrf_required = False
        if namespace_handlers:
            auth_required = bool(namespace_handlers[0].requires_auth())
            csrf_required = bool(namespace_handlers[0].requires_csrf())
            for handler in namespace_handlers[1:]:
                if bool(handler.requires_auth()) != auth_required or bool(handler.requires_csrf()) != csrf_required:
                    raise ValueError(f"WebSocket namespace {namespace!r} has mixed auth/csrf requirements")

        @socketio_server.on("connect", namespace=namespace)
        async def _connect(sid, environ, _auth, _namespace=namespace, _auth_required=auth_required, _csrf_required=csrf_required):
            with webapp.request_context(environ):
                origin_ok, origin_reason = validate_ws_origin(environ)
                if not origin_ok:
                    PrintStyle.warning(f"WebSocket origin validation failed for {_namespace} {sid}: {origin_reason or 'invalid'}")
                    return False
                if _auth_required:
                    credentials_hash = login.get_credentials_hash()
                    if credentials_hash:
                        if session.get("authentication") != credentials_hash:
                            PrintStyle.warning(f"WebSocket authentication failed for {_namespace} {sid}: session not valid")
                            return False
                    else:
                        PrintStyle.debug("WebSocket authentication required but credentials not configured; proceeding")
                if _csrf_required:
                    expected_token = session.get("csrf_token")
                    if not isinstance(expected_token, str) or not expected_token:
                        PrintStyle.warning(f"WebSocket CSRF validation failed for {_namespace} {sid}: csrf_token not initialized")
                        return False
                    auth_token = None
                    if isinstance(_auth, dict):
                        auth_token = _auth.get("csrf_token") or _auth.get("csrfToken")
                    if not isinstance(auth_token, str) or not auth_token:
                        PrintStyle.warning(f"WebSocket CSRF validation failed for {_namespace} {sid}: missing csrf_token in auth")
                        return False
                    if auth_token != expected_token:
                        PrintStyle.warning(f"WebSocket CSRF validation failed for {_namespace} {sid}: csrf_token mismatch")
                        return False
                    cookie_name = f"csrf_token_{runtime.get_runtime_id()}"
                    cookie_token = request.cookies.get(cookie_name)
                    if cookie_token != expected_token:
                        PrintStyle.warning(f"WebSocket CSRF validation failed for {_namespace} {sid}: csrf cookie mismatch")
                        return False
                user_id = session.get("user_id") or "single_user"
                await websocket_manager.handle_connect(_namespace, sid, user_id=user_id)
                return True

        @socketio_server.on("disconnect", namespace=namespace)
        async def _disconnect(sid, _namespace=namespace):
            await websocket_manager.handle_disconnect(_namespace, sid)

        def _register_socketio_event(event_type):
            @socketio_server.on(event_type, namespace=namespace)
            async def _event_handler(sid, data, _event_type=event_type, _namespace=namespace):
                payload = data or {}
                return await websocket_manager.route_event(_namespace, _event_type, payload, sid)

        for _event_type in websocket_manager.iter_event_types(namespace):
            _register_socketio_event(_event_type)

        @socketio_server.on("*", namespace=namespace)
        async def _catch_all(event, sid, data, _namespace=namespace):
            payload = data or {}
            return await websocket_manager.route_event(_namespace, event, payload, sid)

    for namespace, namespace_handlers in namespace_map.items():
        _register_namespace_handlers(namespace, namespace_handlers)

    return allowed_namespaces


def run():
    PrintStyle().print("正在初始化框架... [中文版]")
    initialize.initialize_migration()
    PrintStyle().print("正在启动服务器...")

    port = 5001  # 中文版使用 5001 端口
    host = runtime.get_arg("host") or dotenv.get_dotenv_value("WEB_UI_HOST") or "localhost"

    def register_api_handler(app, handler):
        name = handler.__module__.split(".")[-1]
        instance = handler(app, lock)

        async def handler_wrap():
            return await instance.handle_request(request=request)

        if handler.requires_loopback():
            handler_wrap = requires_loopback(handler_wrap)
        if handler.requires_auth():
            handler_wrap = requires_auth(handler_wrap)
        if handler.requires_api_key():
            handler_wrap = requires_api_key(handler_wrap)
        if handler.requires_csrf():
            handler_wrap = csrf_protect(handler_wrap)

        app.add_url_rule(f"/{name}", f"/{name}", handler_wrap, methods=handler.get_methods())

    handlers = load_classes_from_folder("python/api", "*.py", ApiHandler)
    for handler in handlers:
        register_api_handler(webapp, handler)

    handlers_by_namespace = _build_websocket_handlers_by_namespace(socketio_server, lock)
    configure_websocket_namespaces(
        webapp=webapp,
        socketio_server=socketio_server,
        websocket_manager=websocket_manager,
        handlers_by_namespace=handlers_by_namespace,
    )

    init_a0()

    wsgi_app = WSGIMiddleware(webapp)
    starlette_app = Starlette(
        routes=[
            Mount("/mcp", app=mcp_server.DynamicMcpProxy.get_instance()),
            Mount("/a2a", app=fasta2a_server.DynamicA2AProxy.get_instance()),
            Mount("/", app=wsgi_app),
        ]
    )

    asgi_app = ASGIApp(socketio_server, other_asgi_app=starlette_app)

    class _UvicornServerWrapper:
        def __init__(self, server):
            self._server = server
        def shutdown(self):
            self._server.should_exit = True

    process.set_server(_UvicornServerWrapper(uvicorn.Server(uvicorn.Config(
        asgi_app,
        host=host,
        port=port,
        log_level="info",
        access_log=_settings.get("uvicorn_access_logs_enabled", False),
        ws="wsproto",
    ))))

    PrintStyle().debug(f"中文版服务器启动中 http://{host}:{port} ...")
    threading.Thread(target=wait_for_health, args=(host, port), daemon=True).start()
    uvicorn.Server(uvicorn.Config(
        asgi_app,
        host=host,
        port=port,
        log_level="info",
        access_log=_settings.get("uvicorn_access_logs_enabled", False),
        ws="wsproto",
    )).run()


def wait_for_health(host, port):
    url = f"http://{host}:{port}/health"
    while True:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    PrintStyle().print("Agent Zero 中文版已启动。")
                    return
        except Exception:
            pass
        time.sleep(1)


def init_a0():
    init_chats = initialize.initialize_chats()
    init_chats.result_sync()
    initialize.initialize_mcp()
    initialize.initialize_job_loop()
    initialize.initialize_preload()


if __name__ == "__main__":
    runtime.initialize()
    dotenv.load_dotenv()
    run()
