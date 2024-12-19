from Logger import error, info, warning, error
from aiohttp import web as aiohttp_web, ClientSession, client_exceptions as aiohttp_web_client_exceptions
from json import loads
import time
import asyncio

ws_id = 0
# servers senf pings and cliuents respond with pongs
class WebSocketBase:
    def __init__(self, name, verbose=0):
        global ws_id

        self.ws = None
        self.name = name
        self.verbose = verbose
        self.pingWaitTask = None
        self.pingSendTask = None
        self.lastPingSent = time.monotonic()
        self.lastPongReceived = time.monotonic()
        self.lastPingReceived = time.monotonic()
        self.pingInterval = 1
        self.pingResponseInterval = 5
        self.url = None
        self.remote = None
        self.closed = False
        self.connected = False
        ws_id += 1
        self.ws_id = ws_id

    async def prepare(self, request):
        self.ws = aiohttp_web.WebSocketResponse(heartbeat=0, autoping=False, autoclose=True,
                                                timeout=1, receive_timeout=self.pingResponseInterval)
        try:
            await self.ws.prepare(request)

            self.pingSendTask = asyncio.create_task(self.ping())
            self.remote = request.remote
            return True
        except Exception as e:
            info("%s: WebSocket(%s:%s): prepare exception=%s: %s", time.monotonic(), self.remote, self.name, type(e).__name__, str(e))
            return False

    async def ping(self):
        if self.verbose > 1:
            info("%s: WebSocket(%s:%s) %s: start pinging", time.monotonic(), self.ws_id, self.remote, self.name)

        #at the start we wait have the regular ping delay before sending a ping
        while self.ws is not None:
            await asyncio.sleep(self.pingInterval)

            if not self.connected:
                continue

            curTime = time.monotonic()
            if self.verbose > 1:
                info("%s: WebSocket(%s:%s) %s: lastPongReceived=%s", curTime, self.remote, self.name, self.lastPongReceived)

            if (self.lastPongReceived + self.pingResponseInterval) < curTime:
                if self.verbose:
                    info("%s: WebSocket(%s:%s) %s: ping timeout", curTime, self.ws_id, self.remote, self.name)

                await self.close(msg="missing pong")

            if self.verbose > 1:
                info("%s: WebSocket(%s:%s) %s: ping", curTime, self.ws_id, self.remote, self.name)

            try:
                await self.ws.send_str("ping")
            except ConnectionResetError:
                await self.close(msg="Connection reset")

            self.lastPingSent = time.monotonic()

    async def waitOnPing(self):
        while self.ws is not None:
            await asyncio.sleep(self.pingInterval)

            if not self.connected:
                continue

            curTime = time.monotonic()

            if self.verbose > 1:
                info("%s: WebSocket(%s:%s) %s: lastPingReceived=%s", curTime, self.ws_id, self.remote, self.name, self.lastPingReceived)

            if (self.lastPingReceived + self.pingResponseInterval) < curTime:
                if self.verbose:
                    info("%s: WebSocket(%s:%s) %s: missing ping", curTime, self.ws_id, self.remote, self.name)

                await self.close(msg="missing ping")

    async def connect(self, url):
        self.url = url
        self.remote = url
        self.connected = False

        info("%s: WebSocket(%s:%s) %s: connect to url=%s", time.monotonic(), self.ws_id, self.remote, self.name, url, stacklevel=2)

        async with ClientSession() as session:
            if self.verbose:
                info("%s: WebSocket(%s:%s) %s: create sessions", time.monotonic(), self.ws_id, self.remote, self.name, stacklevel=2)

            try:
                async with session.ws_connect(url, receive_timeout=self.pingResponseInterval, timeout=5) as ws:
                    info("%s: WebSocket(%s:%s) %s: connected ws=%s", time.monotonic(), self.ws_id, self.remote, self.name, self.ws, stacklevel=2)

                    self.ws = ws
                    if not self.pingWaitTask:
                        self.pingWaitTask = asyncio.create_task(self.waitOnPing())

                    self.lastPongReceived = time.monotonic()
                    self.lastPingReceived = time.monotonic()
                    self.connected = True

                    await self.onconnect()
                    try:
                        msg = await self._process()
                    except Exception as e:
                        msg = "uncaught exception 1"
                        error("%s: WebSocket(%s:%s) %s: connected ws=%s", time.monotonic(), self.ws_id, self.remote, self.name, self.ws, stack_info=True, exc_info=True, stacklevel=2)

                    if msg:
                        await self.onerror(msg)

            except Exception as e:
                msg = "uncaught exception 2"
                error("%s: WebSocket(%s:%s) %s: connected ws=%s", time.monotonic(), self.ws_id, self.remote, self.name, self.ws, stack_info=True, exc_info=True, stacklevel=2)

            self.connected = False
            await self.close()

    async def process(self):
        self.connected = True

        await self.onconnect()
        while True:
            self.lastPongReceived = time.monotonic()
            self.lastPingReceived = time.monotonic()

            msg = await self._process()

            if msg:
                break

            if self.ws.closed:
                break

        await self.close(msg)

    async def _process(self):
        try:
            if self.verbose:
                info("%s: WebSocket(%s:%s) %s: process wait", time.monotonic(), self.ws_id, self.remote, self.name)

            async for msg in self.ws:
                if self.ws is None or self.ws.closed:
                    break

                if msg.type == aiohttp_web.WSMsgType.TEXT:
                    if msg.data == "pong":
                        if self.verbose > 1:
                            info("%s: WebSocket(%s:%s) %s: pong received", time.monotonic(), self.ws_id, self.remote, self.name)

                        self.lastPongReceived = time.monotonic()
                    elif msg.data == "ping":
                        if self.verbose > 1:
                            info("%s: WebSocket(%s:%s) %s: ping receieved; send pong", time.monotonic(), self.ws_id, self.remote, self.name)

                        self.lastPingReceived = time.monotonic()
                        await self.ws.send_str("pong")
                    else:
                        decodedMsg = loads(msg.data)

                        if "error" in decodedMsg:
                            errorMsg = decodedMsg["error"]
                            info("%s: WebSocket(%s:%s) %s: received error=%s", time.monotonic(), self.ws_id, self.name, self.remote, errorMsg)

                            self.onerror("remote error: " + errorMsg)
                        else:
                            cmd = decodedMsg.get("cmd", None)
                            cmdFnName = f"cmd_{cmd}"
                            try:
                                cmdFn = getattr(self, cmdFnName)
                            except AttributeError:
                                await self.onerror(f"Websocket: unhandled cmd {cmd} msg={decodedMsg}")
                                continue

                            data = decodedMsg.get("data", {})
                            if self.verbose:
                                info("%s: WebSocket(%s:%s) %s: received cmd=%s data=%s", time.monotonic(), self.ws_id, self.remote, self.name, cmdFnName, data)

                            await cmdFn(data)

                elif msg.type == aiohttp_web.WSMsgType.ERROR:
                    info("%s: WebSocket(%s:%s) %s: WSMsgType=ERROR exc=%s", time.monotonic(), self.ws_id, self.remote, self.name, self.ws.exception())

                    self.onerror("WSMsgType=ERROR: " + self.ws.exception())
                else:
                    warning("%s: WebSocket(%s:%s) %s: bad type data=%s", time.monotonic(), self.ws_id, self.remote, self.name, msg.type, msg.data)
        except ConnectionResetError:
            return "connection reset"
        except asyncio.TimeoutError:
            return "timeout"

        return None

    async def send_msg(self, cmd, data=None):
        if self.verbose:
            info("%s: WebSocket(%s:%s) %s: send cmd=%s data=%s", time.monotonic(), self.ws_id, self.remote, self.name, cmd, data, stacklevel=2)

        try:
            await self.ws.send_json({"cmd": cmd, "data": data})
            return True
        except ConnectionResetError as exception:
            error("%s: WebSocket(%s:%s) %s: send cmd=%s data=%s exc=%s", time.monotonic(), self.ws_id, self.remote, self.name, cmd, data, exception, stacklevel=2)
        except Exception as exception:
            error("%s: WebSocket(%s:%s) %s: send cmd=%s data=%s exc=%s ws=%s", time.monotonic(), self.ws_id, self.remote, self.name, cmd, data, exception, self.ws, stacklevel=2)

        await self.close()

        return False

    async def close(self, msg=None):
        self.closed = True

        info("%s: WebSocket(%s:%s) %s: close error=%s", time.monotonic(), self.ws_id, self.remote, self.name, msg, stacklevel=2)

        if msg:
            await self.onerror(msg);

        if self.pingWaitTask is not None:
            self.pingWaitTask.cancel()
            self.pingWaitTask = None

        if self.pingSendTask is not None:
            self.pingSendTask.cancel()
            self.pingSendTask = None

        if self.ws:
            await self.ws.close()
            self.ws = None

        await self.onclose()

    async def onerror(self, msg):
        error("%s: WebSocket(%s:%s) %s: onerror=%s", time.monotonic(), self.ws_id, self.remote, self.name, msg, stacklevel=2)

    async def onclose(self):
        info("%s: WebSocket(%s:%s) %s: closed", time.monotonic(), self.ws_id, self.remote, self.name, stacklevel=2)

    async def onconnect(self):
        info("%s: WebSocket(%s:%s) %s: connected", time.monotonic(), self.ws_id, self.remote, self.name, stacklevel=2)
