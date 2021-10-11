from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor


SERVER_HOST = 'localhost'
SERVER_PORT = 10002

class CurrencyProtocol(Protocol):

    rates = b''

    def dataReceived(self, data):
        print 'data received'
        self.rates += data

    def connectionLost(self, reason):
        print 'connection lost', reason
        self.ratesReceived(self.rates)

    def ratesReceived(self, rates):
        self.factory.rates_finished(rates)


class CurrencyClientFactory(ClientFactory):

    protocol = CurrencyProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def rates_finished(self, rates):
        if self.deferred is not None:
            deferred, self.deferred = self.deferred, None
            deferred.callback(rates)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            deferred, self.deferred = self.deferred, None
            deferred.errback(reason)


def get_rates(host, port):
    deferred = defer.Deferred()
    from twisted.internet import reactor
    factory = CurrencyClientFactory(deferred)
    reactor.connectTCP(host, port, factory)
    return deferred

def main():

    @defer.inlineCallbacks
    def get_currency_rates(host, port):
        try:
            rates = yield get_rates(host, port)
        except Exception as e:
            print 'rates download failed', e
            raise

        defer.returnValue(rates)

    def print_rates(rates):
        print rates
        print 'done'
        reactor.stop()

    d = get_rates(SERVER_HOST, SERVER_PORT)
    d.addCallbacks(print_rates)
    reactor.run()

if __name__ == '__main__':
    main()
