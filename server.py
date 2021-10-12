from twisted.internet.protocol import ServerFactory, Protocol
from twisted.web.client import Agent, ResponseDone
from twisted.internet import defer


PORT = 8000
HOST = "localhost"
EXTERNAL_SERVER_URL = ""  # add api url here


class CurrencyProtocol(Protocol):

    def dataReceived(self, data):
        print "received: ", data
        self.sendData(data)

    def connectionMade(self):
        print "connection made"

    def connectionLost(self, reason):
        print "connection lost", reason

    def sendData(self, data):
        deferredRates = self.factory.obtainRates(data)
        deferredRates.addCallbacks(self.transport.write, self.sendErrorValue)

    def sendErrorValue(self, failure):
        self.transport.write(str(failure.value))


class CurrencyServerFactory(ServerFactory):

    protocol = CurrencyProtocol

    def __init__(self, agent):
        self.agent = agent

    def obtainRates(self, data):
        return self.agent.performRequest(data)


class HttpAgentHandler(object):

    def __init__(self, agent, url):
        self.agent = agent
        self.url = url

    def performRequest(self, data):
        url = self.url + data + "/"
        response = self.agent.request(b"GET", url)
        return response.addCallback(self.handleResponse)

    def handleResponse(self, response):
        finished =defer.Deferred()
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
            self.deferred.callback(responseInfo)
        else:
            self.deferred.errback(reason)

    def cleanDeferred(self, value):
        if self.deferred is not None:
            self.deferred = None




def main():
    from twisted.internet import reactor
    agent = Agent(reactor)
    httpAgentHandler = HttpAgentHandler(agent, EXTERNAL_SERVER_URL)
    factory = CurrencyServerFactory(httpAgentHandler)
    reactor.listenTCP(port=PORT, interface=HOST, factory=factory)
    reactor.run()

if __name__ == "__main__":
    main()
