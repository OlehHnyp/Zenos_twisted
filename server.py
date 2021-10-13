import json
import os
import time

from twisted.internet.protocol import ServerFactory, Protocol
from twisted.web.client import Agent, ResponseDone
from twisted.internet import defer


PORT = 8123
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
        """
        Obtain currency rate (or error) and send it to the client.
        :param data: str
        :return: None
        """
        deferredRates = self.factory.obtainRates(data)
        deferredRates.addCallbacks(self.transport.write, self.sendErrorValue)

    def sendErrorValue(self, failure):
        """
        Send error information to the client.
        :param failure: Failure
        :return: None
        """
        response = dict.fromkeys(self.factory.fieldnames)
        response["error"] = str(failure.value)
        response = json.dumps(response)
        self.transport.write(response)


class CurrencyServerFactory(ServerFactory):

    protocol = CurrencyProtocol

    def __init__(self, agent, buf):
        """
        Initialize CurrencyServerFactory instance.
        :param agent: HttpAgentHandler instance
        :param buf: HttpBodyHandler instance
        """
        self.agent = agent  # class instance for handling http requests
        self.bufferHandler = buf  # class instance for handling buffered data
        self.bufferData = self.bufferHandler.getBufferData()  # obtain buffered data
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
        """
        Provide obtaining rates from the buffer or API.
        :param currencies: str
        :return: Deferred
        """
        validRates = self.getValidRates(currencies)  # check if the buffer stores valid data
        if validRates:
            rates = yield validRates
            print 'got from buffer ', currencies
        else:
            rates = yield self.agent.performRequest(currencies)  # perform request to API
            rates = yield self.setFields(rates)  # delete unnecessary fields and add error field
            rates = yield self.addToBufferData(rates, currencies)
            print 'got from API ', currencies

        defer.returnValue(rates)

    def addToBufferData(self, data, currencies):
        """
        Add currency rate to the buffer.
        :param data: str
        :param currencies: str
        :return: str
        """
        self.bufferData[currencies] = json.loads(data)
        self.bufferHandler.reWriteBufferFile(self.bufferData)
        return data

    def getValidRates(self, currencies):
        """
        Check if buffer stores valid currency rate and return it or None.
        :param currencies: str
        :return: str or None
        """
        rates = self.bufferData.get(currencies)
        if rates and rates.get("time_next_update_unix") > time.time():
            return json.dumps(rates)
        return None

    def setFields(self, response):
        """
        Delete unnecessary fields and add error field to API response data.
        :param response: str
        :return: str
        """
        response = json.loads(response)
        self._deleteUnnecessaryData(response)
        self._addErrorField(response)
        response = json.dumps(response)
        return response

    @staticmethod
    def _deleteUnnecessaryData(response):
        """
        Delete unnecessary fields from API response data.
        :param response: dict
        :return: dict
        """
        del response["documentation"]
        del response["terms_of_use"]
        return response

    @staticmethod
    def _addErrorField(response):
        """
        Add error field to API response data.
        :param response: dict
        :return: dict
        """
        response['error'] = None
        return response


class HttpAgentHandler(object):
    """
    Class for handling http requests.
    """

    def __init__(self, agent, url, bodyHandler):
        """
        Initialize HttpAgentHandler instance.
        :param agent: twisted.web.client.Agent
        :param url: str
        :param bodyHandler: classobj
        """
        self.agent = agent
        self.url = url  # external API url
        self.bodyHandler = bodyHandler  # class for handling response body

    def performRequest(self, data):
        """
        Send request to external API url.
        :param data: str
        :return: Deferred
        """
        url = self.url + data + "/"
        response = self.agent.request(b"GET", url)
        return response.addCallback(self.handleResponse)

    def handleResponse(self, response):
        """
        Obtain response body.
        :param response: twisted.web._newclient.Response
        :return: Deferred
        """
        finished = defer.Deferred()
        response.deliverBody(self.bodyHandler(finished, response.code, response.phrase))
        return finished


class HttpBodyHandler(Protocol):
    """
    Class for obtaining response body.
    """

    body = b""

    def __init__(self, deferred, code, phrase):
        """
        Initialize HttpBodyHandler instance.
        :param deferred: Deferred
        :param code: int
        :param phrase: str
        """
        self.deferred = deferred
        self.code = code  # response status code
        self.phrase = phrase  # response status info

    def dataReceived(self, data):
        self.body += data

    def connectionLost(self, reason):
        """
        Fire deferred according to conditions.
        :param reason: Failure
        :return:None
        """
        self.deferred.addBoth(self.cleanDeferred)
        if reason.check(ResponseDone) and self.code == 200:
            self.deferred.callback(self.body)
        elif reason.check(ResponseDone):  # if request didn't succeed add response code and status into Failure
            responseInfo = "{} {}".format(self.code, self.phrase)
            self.deferred.errback(Exception(responseInfo))
        else:
            self.deferred.errback(reason)

    def cleanDeferred(self, value):
        """
        Prevent reusing fired deferred.
        :param value: None
        :return: None
        """
        if self.deferred is not None:
            self.deferred = None


class BufferHandler(object):
    """
    Class for handling response body.
    """

    def __init__(self, bufferFile):
        """
        Initialize BufferHandler instance.
        :param bufferFile: str
        """
        self._bufferFile = bufferFile

    def reWriteBufferFile(self, data):
        """
        Clear buffer file and write new data.
        :param data: dict
        :return: None
        """
        with open(self._bufferFile, "w") as f:
            json.dump(data, f)
    
    def getBufferData(self):
        """
        Return buffered data from buffer file if exists.
        :return: dict or None
        """
        if self._bufferExists():
            with open(self._bufferFile, "r") as f:
                bufferData = json.load(f)
            return bufferData
        return {}
    
    def _bufferExists(self):
        """
        Check if buffer file exists and not empty
        :return: bool
        """
        return os.path.isfile(self._bufferFile) and os.path.getsize(self._bufferFile) > 0


def main():
    """
    Create factory and relative objects, create TCP listener and run reactor.
    :return: None
    """
    buf = BufferHandler(BUFFER_FILE)
    from twisted.internet import reactor
    agent = Agent(reactor)
    httpAgentHandler = HttpAgentHandler(agent, EXTERNAL_SERVER_URL, HttpBodyHandler)
    factory = CurrencyServerFactory(httpAgentHandler, buf)
    reactor.listenTCP(port=PORT, interface=HOST, factory=factory)
    reactor.run()

if __name__ == "__main__":
    main()
