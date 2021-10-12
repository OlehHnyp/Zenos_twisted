from twisted.internet.protocol import ServerFactory, Protocol
from twisted.web.client import Agent, ResponseDone
from twisted.internet import defer


PORT = 8000
HOST = 'localhost'
EXTERNAL_SERVER_URL = ''  # add api url here


class CurrencyProtocol(Protocol):

    def dataReceived(self, data):
        print 'received: ', data
        self.sendData()

    def connectionMade(self):
        print 'connection made'

    def connectionLost(self, reason):
        print 'connection lost', reason

    def sendData(self):
        deferred_rates = self.factory.obtainRates()
        deferred_rates.addCallbacks(self.transport.write, self.sendErrorValue)

    def sendErrorValue(self, failure):
        self.transport.write(failure.value)


class CurrencyServerFactory(ServerFactory):

    protocol = CurrencyProtocol

    def __init__(self, agent):
        self.agent = agent

    def obtainRates(self):
        return self.agent.performRequest()


class HttpAgentHandler(object):

    def __init__(self, agent, url):
        self.agent = agent
        self.url = url

    def performRequest(self):
        response = self.agent.request(b"GET", self.url)
        return response.addCallback(self.handleResponse)

    def handleResponse(self, response):
        finished =defer.Deferred()
        response.deliverBody(HttpBodyHandler(finished))
        return finished


class HttpBodyHandler(Protocol):

    body = b''

    def __init__(self, deferred):
        self.deferred = deferred

    def dataReceived(self, data):
        self.body += data

    def connectionLost(self, reason):
        if reason.check(ResponseDone):
            self.deferred.callback(self.body)
        else:
            self.deferred.errback(reason)





def main():
    from twisted.internet import reactor
    agent = Agent(reactor)
    httpAgentHandler = HttpAgentHandler(agent, EXTERNAL_SERVER_URL)
    factory = CurrencyServerFactory(httpAgentHandler)
    reactor.listenTCP(port=PORT, interface=HOST, factory=factory)
    reactor.run()

if __name__ == '__main__':
    main()
