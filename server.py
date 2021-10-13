import json
import os
import time

from twisted.internet.protocol import ServerFactory, Protocol
from twisted.web.client import Agent, ResponseDone
from twisted.internet import defer


PORT = 8000
HOST = "localhost"
EXTERNAL_SERVER_URL = ""  # add api url here
BUFFER_FILE = "serverData/buffer.txt"


class CurrencyProtocol(Protocol):

    def dataReceived(self, data):
        self.sendData(data)

    def connectionMade(self):
        print "connection made"

    def connectionLost(self, reason):
        print "connection lost", reason

    def sendData(self, data):
        deferredRates = self.factory.obtainRates(data)
        deferredRates.addCallbacks(self.transport.write, self.sendErrorValue)

    def sendErrorValue(self, failure):
        response = dict.fromkeys(self.factory.fieldnames)
        response["error"] = str(failure.value)
        response = json.dumps(response)
        self.transport.write(response)


class CurrencyServerFactory(ServerFactory):

    protocol = CurrencyProtocol

    def __init__(self, agent, buf):
        self.agent = agent
        self.bufferHandler = buf
        self.bufferData = self.bufferHandler.getBufferData()
        self.fieldnames = [
            "result",
            "base_code",
            "target_code",
            "conversion_rate",
            "time_last_update_utc",
            "time_last_update_unix",
            "time_next_update_utc",
            "time_next_update_unix",
            "error",
        ]

    @defer.inlineCallbacks
    def obtainRates(self, currencies):
        validRates = self.getValidRates(currencies)
        if validRates:
            rates = yield validRates
            print 'got from buffer ', currencies
        else:
            rates = yield self.agent.performRequest(currencies)
            rates = yield self.setFields(rates)
            rates = yield self.addToBufferData(rates, currencies)
            print 'got from API ', currencies

        defer.returnValue(rates)

    def addToBufferData(self, data, currencies):
        self.bufferData[currencies] = json.loads(data)
        self.bufferHandler.reWriteBufferFile(self.bufferData)
        return data

    def getValidRates(self, currencies):
        rates = self.bufferData.get(currencies)
        if rates and rates.get("time_next_update_unix") > time.time():
            return json.dumps(rates)
        return None

    def setFields(self, response):
        response = json.loads(response)
        self._deleteUnnecessaryData(response)
        self._addErrorField(response)
        response = json.dumps(response)
        return response

    @staticmethod
    def _deleteUnnecessaryData(response):
        del response["documentation"]
        del response["terms_of_use"]
        return response

    @staticmethod
    def _addErrorField(response):
        response['error'] = None
        return response


class HttpAgentHandler(object):

    def __init__(self, agent, url):
        self.agent = agent
        self.url = url

    def performRequest(self, data):
        url = self.url + data + "/"
        response = self.agent.request(b"GET", url)
        return response.addCallback(self.handleResponse)

    def handleResponse(self, response):
        finished = defer.Deferred()
        response.deliverBody(HttpBodyHandler(finished, response.code, response.phrase))
        return finished


class HttpBodyHandler(Protocol):

    body = b""

    def __init__(self, deferred, code, phrase):
        self.deferred = deferred
        self.code = code
        self.phrase = phrase

    def dataReceived(self, data):
        self.body += data

    def connectionLost(self, reason):
        self.deferred.addBoth(self.cleanDeferred)
        if reason.check(ResponseDone) and self.code == 200:
            self.deferred.callback(self.body)
        elif reason.check(ResponseDone):
            responseInfo = "{} {}".format(self.code, self.phrase)
            self.deferred.errback(Exception(responseInfo))
        else:
            self.deferred.errback(reason)

    def cleanDeferred(self, value):
        if self.deferred is not None:
            self.deferred = None


class BufferHandler(object):

    def __init__(self, bufferFile):
        self._bufferFile = bufferFile

    def reWriteBufferFile(self, data):
        with open(self._bufferFile, "w") as f:
            json.dump(data, f)
    
    def getBufferData(self):
        if self._bufferExists():
            with open(self._bufferFile, "r") as f:
                bufferData = json.load(f)
            return bufferData
        return {}
    
    def _bufferExists(self):
        return os.path.isfile(self._bufferFile) and os.path.getsize(self._bufferFile) > 0


def main():
    buf = BufferHandler(BUFFER_FILE)
    from twisted.internet import reactor
    agent = Agent(reactor)
    httpAgentHandler = HttpAgentHandler(agent, EXTERNAL_SERVER_URL)
    factory = CurrencyServerFactory(httpAgentHandler, buf)
    reactor.listenTCP(port=PORT, interface=HOST, factory=factory)
    reactor.run()

if __name__ == "__main__":
    main()
