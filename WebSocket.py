from Logger import error
from aiohttp import web as aiohttp_web, ClientSession
from json import loads
import time
import asyncio

# servers senf pings and cliuents respond with pongs
class WebSocketBase:
    def __init__(self, name, verbose=False):
        self.ws = None
        self.name = name
        self.verbose = verbose
        self.pingTask = None
        self.lastPingSent = time.monotonic()
        self.lastPongReceived = time.monotonic()
        self.lastPingReceived = time.monotonic()
        self.pingDelay = 10
        
    async def prepare(self, request):
        self.ws = aiohttp_web.WebSocketResponse(heartbeat=0, autoping=False, autoclose=True, timeout=1, receive_timeout=self.pingDelay * 1.5)
        await self.ws.prepare(request)

        self.pingTask = asyncio.ensure_future(self.ping())

    async def ping(self):
        if self.verbose:
            print(f"{self.name}: start pinging")
            
        while True:
            curTime = time.monotonic()
            if self.verbose:
                print(f"{self.name}: {self.lastPongReceived=} {curTime=}")
                
            if (self.lastPongReceived + 1.5 * self.pingDelay) < curTime:
                if self.verbose:
                    print(f"{self.name}: ping timeout")
                    
                await self.close()
                return;
            
            if self.verbose:
                print(f"{self.name}: ping")
                
            await self.ws.send_str("ping")
            self.lastPingSent = time.monotonic()
            await asyncio.sleep(self.pingDelay)

    async def waitOnPing(self):
        while True:
            curTime = time.monotonic()

            if self.verbose:
                print(f"{self.name}: {self.lastPingReceived=} {curTime=}")
                
            if (lastPingReceived + 1.5 * self.pingDelay) < curTime:
                if self.verbose:
                    print(f"{self.name}: missing ping")
                    
                await self.close()
                return;

            await asyncio.sleep(self.pingDelay)

    async def connect(self, url):
        if self.verbose:
            print(f"{self.name}: connect to {url=}")
            
        async with ClientSession() as session:
            if self.verbose:
                print(f"{self.name}: create session")
                
            async with session.ws_connect(url, receive_timeout=self.pingDelay * 1.5, timeout=1) as ws:
                if self.verbose:
                    print(f"{self.name}: connected {ws=}")
                    
                self.ws = ws
                self.pingTask = asyncio.ensure_future(self.waitOnPing())
                await self.process()
        
    async def process(self):
        try:
            if self.verbose:
                print(f"{self.name}: process wait")
                
            async for msg in self.ws:
                if self.verbose:
                    print(f"{self.name}: websocket: ", msg)
                    
                if msg.type == aiohttp_web.WSMsgType.TEXT:
                    if msg.data == 'close':
                        await self.close()
                        return
                    elif msg.data == "pong":
                        if self.verbose:
                            print(f"{self.name}: pong")
                            
                        self.lastPongReceived = time.monotonic()
                    elif msg.data == "ping":
                        if self.verbose:
                            print(f"{self.name}: ping; send pong")
                                
                        self.lastPongReceived = time.monotonic()
                        await self.ws.send_str("pong")
                    else:
                        decodedMsg = loads(msg.data)
                        cmd = decodedMsg.get("cmd", None)
                        cmdFnName = f"cmd_{cmd}"
                        try:
                            cmdFn = getattr(self, cmdFnName)
                        except AttributeError:
                            await self.onerror(f"Websocket: unhandled cmd {cmd} msg={decodedMsg}")
                            
                        data = decodedMsg.get("data", {})
                        await cmdFn(data)
                elif msg.type == aiohttp_web.WSMsgType.ERROR:
                    await self.onerror(self.ws.exception())

                else:
                    print(f"{self.name}: {msg.type=}")
                    
        except ConnectionResetError as e:
            await self.onerror(e)
            pass
        except asyncio.TimeoutError as e:
            await self.onerror(e)
            pass

        await self.close()

    async def send_msg(self, cmd, data=None):
        if self.verbose:
            print(f"{self.name}: ws send {cmd=} {data=}")
            
        try:
            await self.ws.send_json({"cmd": cmd, "data": data})
            return True
        except (RuntimeError, ConnectionResetError):
            await self.closed()
            return False

    async def close(self):
        if self.verbose:
            print(f"{self.name}: close")

        if self.pingTask is not None:
            self.pingTask.cancel()
            self.pingTask = None

        if self.ws:
            if self.verbose:
                print(f"{self.name}: send close")
            
            try:
                await self.ws.send_str("close")
            except ConnectionResetError:
                pass
            
            if self.verbose:
                print(f"{self.name}: close ws={self.ws}")
                
            await self.ws.close()
            self.ws = None

            await self.closed()

    async def onerror(self, exception):
        if self.verbose:
            print(f"{self.name}: WebSocket: connection exception {exception}")
            
        error("WebSocket: connection exception %s", exception)
        
    async def closed(self):
        if self.verbose:
            print(f"{self.name}: closed")

        
