from aiohttp import web as aiohttp_web, ClientSession, client_exceptions as aiohttp_web_client_exceptions
from json import loads
import time
import asyncio
from logger import error, info, warning

ws_id = 0
# servers senf pings and cliuents respond with pongs
class WebSocketBase:
    def __init__(self, name, verbose=0):
        global ws_id

        self.ws = None
        self.name = name
        self.verbose = verbose
        self.verbose = False
        self.ping_wait_task = None
        self.ping_send_task = None
        self.last_ping_sent = time.monotonic()
        self.last_pong_received = time.monotonic()
        self.last_ping_received = time.monotonic()
        self.ping_interval = 1
        self.ping_response_interval = 5
        self.url = None
        self.remote = None
        self.closed = False
        self.connected = False
        ws_id += 1
        self.ws_id = ws_id
        self.verbose=True

    async def prepare(self, request):
        self.ws = aiohttp_web.WebSocketResponse(heartbeat=5, autoping=True, autoclose=True,
                                                timeout=1, receive_timeout=self.ping_response_interval)
        try:
            await self.ws.prepare(request)

            self.ping_send_task = asyncio.create_task(self.ping())
            self.remote = request.remote
            return True
        except Exception as e:
            info("%s: WebSocket(%s:%s): prepare exception=%s: %s; url=%s remote=%s",
                 time.monotonic(), self.remote, self.name,
                 type(e).__name__, str(e),
                 self.url, self.remote)
            return False

    async def ping(self):
        if self.verbose > 1:
            info("%s: WebSocket(%s:%s) start pinging; url=%s remote=%s",
                 time.monotonic(), self.ws_id, self.name,
                 self.url, self.remote)

        #at the start we wait have the regular ping delay before sending a ping
        while self.ws is not None:
            await asyncio.sleep(self.ping_interval)

            if not self.connected:
                continue

            curTime = time.monotonic()
            if self.verbose > 1:
                info("%s: WebSocket(%s:%s): last_pong_received=%s; url=%s remote=%s",
                     curTime, self.ws_id, self.name.
                     self.last_pong_received,
                     self.url, self.remote)

            if (self.last_pong_received + self.ping_response_interval) < curTime:
                if self.verbose:
                    info("%s: WebSocket(%s:%s): ping timeout; url=%s remote=%s",
                         curTime, self.ws_id, self.name,
                         self.url, self.remote)

                await self.close(msg="send ping -> missing pong")

            if self.verbose > 1:
                info("%s: WebSocket(%s:%s): ping; url=%s remote=%s",
                     curTime, self.ws_id, self.name,
                     self.url, self.remote)

            try:
                await self.ws.send_str("ping")
                self.last_ping_sent = time.monotonic()
            except ConnectionResetError:
                await self.close(msg="send ping -> Connection reset")


    async def wait_on_ping(self):
        while self.ws is not None:
            await asyncio.sleep(self.ping_interval)

            if not self.connected:
                continue

            curTime = time.monotonic()

            if self.verbose > 1:
                info("%s: WebSocket(%s:%s): last_ping_received=%s; url=%s remote=%s",
                     curTime, self.ws_id, self.name,
                     self.last_ping_received,
                     self.url, self.remote)

            if (self.last_ping_received + self.ping_response_interval) < curTime:
                if self.verbose:
                    info("%s: WebSocket(%s:%s): missing ping; url=%s remote=%s",
                         curTime, self.ws_id, self.name,
                         self.url, self.remote)

                await self.close(msg="missing ping")

    async def connect(self, url):
        self.url = url
        self.remote = url
        self.connected = False

        info("%s: WebSocket(%s:%s): connect to; url=%s remote=%s",
             time.monotonic(), self.ws_id, self.name,
             self.url, self.remote, stacklevel=2)

        async with ClientSession() as session:
            if self.verbose:
                info("%s: WebSocket(%s:%s): create sessions; url=%s remote=%s",
                     time.monotonic(), self.ws_id, self.name,
                     self.url, self.remote, stacklevel=2)

            try:
                async with session.ws_connect(url, receive_timeout=self.ping_response_interval, timeout=5) as ws:
                    info("%s: WebSocket(%s:%s): connected ws=%s url=%s remote=%s",
                         time.monotonic(), self.ws_id, self.name,
                         self.ws,
                         self.url, self.remote, stacklevel=2)

                    self.ws = ws
                    if not self.ping_wait_task:
                        self.ping_wait_task = asyncio.create_task(self.wait_on_ping())

                    self.last_pong_received = time.monotonic()
                    self.last_ping_received = time.monotonic()
                    self.connected = True

                    await self.onconnect()
                    try:
                        msg = await self._process()
                    except Exception as e:
                        msg = "uncaught exception 1"
                        error("%s: WebSocket(%s:%s): connected ws=%s; url=%s remote=%s",
                              time.monotonic(), self.ws_id, self.name,
                              self.ws,
                              self.url, self.remote, 
                              stack_info=True, exc_info=True, stacklevel=2)

                    if msg:
                        await self.onerror(msg)

            except Exception as e:
                msg = "uncaught exception 2"
                error("%s: WebSocket(%s:%s): connected ws=%s; url=%s remote=%s",
                      time.monotonic(), self.ws_id, self.name,
                      self.ws,
                      self.url, self.remote,
                      stack_info=True, exc_info=True, stacklevel=2)

            self.connected = False
            await self.close()

    async def process(self):
        self.connected = True
        ws = self.ws

        await self.onconnect()
        while True:
            self.last_pong_received = time.monotonic()
            self.last_ping_received = time.monotonic()

            msg = await self._process()

            if msg:
                break

            if self.ws.closed:
                if self.verbose:
                    info("%s: WebSocket(%s:%s): process ws.closes; url=%s remote=%s",
                         time.monotonic(), self.ws_id, self.name,
                         self.url, self.remote)

                    msg = "remote close detected"
                break

        await self.close(msg)

        return ws

    async def _process(self):
        try:
            if self.verbose:
                info("%s: WebSocket(%s:%s): process wait; url=%s remote=%s",
                     time.monotonic(), self.ws_id, self.name,
                     self.url, self.remote)

            async for msg in self.ws:
                if self.ws is None or self.ws.closed:
                    if self.verbose:
                        info("%s: WebSocket(%s:%s): process ws=%s; url=%s remote=%s",
                             time.monotonic(), self.ws_id, self.name,
                             self.ws,
                             self.url, self.remote, stack_info=2)

                    break

                if msg.type == aiohttp_web.WSMsgType.TEXT:
                    if msg.data == "pong":
                        if self.verbose > 1:
                            info("%s: WebSocket(%s:%s): pong received; url=%s remote=%s",
                                 time.monotonic(), self.ws_id, self.name,
                                 self.url, self.remote)

                        self.last_pong_received = time.monotonic()
                    elif msg.data == "ping":
                        if self.verbose > 1:
                            info("%s: WebSocket(%s:%s): ping receieved; send pong; url=%s remote=%s",
                                 time.monotonic(), self.ws_id, self.name,
                                 self.url, self.remote)

                        self.last_ping_received = time.monotonic()
                        await self.ws.send_str("pong")
                    else:
                        decoded_msg = loads(msg.data)

                        if "error" in decoded_msg:
                            error_msg = decoded_msg["error"]
                            info("%s: WebSocket(%s:%s): received error=%s; url=%s remote=%s",
                                 time.monotonic(), self.ws_id, self.name,
                                 error_msg,
                                 self.url, self.remote)

                            self.onerror("remote error: " + error_msg)
                        else:
                            cmd = decoded_msg.get("cmd", None)
                            cmd_fn_name = f"cmd_{cmd}"
                            try:
                                cmdFn = getattr(self, cmd_fn_name)
                            except AttributeError:
                                await self.onerror(f"Websocket: unhandled cmd {cmd} msg={decoded_msg}")
                                continue

                            data = decoded_msg.get("data", {})
                            if self.verbose:
                                info("%s: WebSocket(%s:%s): received cmd=%s data=%s; url=%s remote=%s",
                                     time.monotonic(), self.ws_id, self.name,
                                     cmd_fn_name, data,
                                     self.url, self.remote)

                            await cmdFn(data)

                elif msg.type == aiohttp_web.WSMsgType.ERROR:
                    info("%s: WebSocket(%s:%s): WSMsgType=ERROR exc=%s; url=%s remote=%s",
                         time.monotonic(), self.ws_id, self.name,
                         self.ws.exception(),
                         self.url, self.remote)

                    self.onerror("WSMsgType=ERROR: " + self.ws.exception())
                else:
                    warning("%s: WebSocket(%s:%s): bad type=%s e data=%s; url=%s remote=%s",
                            time.monotonic(), self.ws_id, self.name,
                            msg.type, msg.data,
                            self.url, self.remote)
        except ConnectionResetError:
            return "connection reset"
        except asyncio.TimeoutError:
            return "timeout"

        return None

    async def send_msg(self, cmd, data=None):
        if self.verbose:
            info("%s: WebSocket(%s:%s): send cmd=%s data=%s; url=%s remote=%s",
                 time.monotonic(), self.ws_id, self.name,
                 cmd, data,
                 self.url, self.remote, stacklevel=2)

        try:
            await self.ws.send_json({"cmd": cmd, "data": data})
            return True
        except ConnectionResetError as exception:
            error("%s: WebSocket(%s:%s): send cmd=%s data=%s exc=%s ws=%s; url=%s remote=%s",
                  time.monotonic(), self.ws_id, self.name,
                  cmd, data, exception, self.ws,
                  self.url, self.remote, stacklevel=2)
        except Exception as exception:
            error("%s: WebSocket(%s:%s): send cmd=%s data=%s exc=%s ws=%s; url=%s remote=%s",
                  time.monotonic(), self.ws_id, self.name,
                  cmd, data, exception, self.ws,
                  self.url, self.remote, stacklevel=2)

        await self.close()

        return False

    async def close(self, msg=None):
        self.closed = True

        info("%s: WebSocket(%s:%s): close msg=%s; url=%s remote=%s",
             time.monotonic(), self.ws_id, self.name,
             msg,
             self.url, self.remote, stacklevel=2)

        if msg:
            await self.onerror(msg)

        if self.ping_wait_task is not None:
            self.ping_wait_task.cancel()
            self.ping_wait_task = None

        if self.ping_send_task is not None:
            self.ping_send_task.cancel()
            self.ping_send_task = None

        if self.ws:
            await self.ws.close()
            self.ws = None

        await self.onclose()

    async def onerror(self, msg):
        error("%s: WebSocket(%s:%s): onerror=%s; url=%s remote=%s",
              time.monotonic(), self.ws_id, self.name,
              msg,
              self.url, self.remote, stacklevel=2)

    async def onclose(self):
        info("%s: WebSocket(%s:%s): closed; url=%s remote=%s",
             time.monotonic(), self.ws_id, self.name,
             self.url, self.remote, stacklevel=2)

    async def onconnect(self):
        info("%s: WebSocket(%s:%s): connected; url=%s remote=%s",
             time.monotonic(), self.ws_id, self.name,
             self.url, self.remote, stacklevel=2)
