from twisted.internet import task
from twisted.internet.protocol import Protocol, ClientFactory


SERVER_HOST = 'localhost'
SERVER_PORT = 8000
CURRENCY = 'USDUAH'
INTERVAL = 5

class CurrencyProtocol(Protocol):

    def connectionMade(self):
        print 'Connection made'
        self.startLoop()

    def dataReceived(self, data):
        print 'data received'
        print data

    def connectionLost(self, reason):
        print 'connection lost', reason

    def startLoop(self):
        self._sender = task.LoopingCall(self.sendRequest)
        self._sender.start(interval=INTERVAL)

    def sendRequest(self):
        self.transport.write(CURRENCY)


class CurrencyClientFactory(ClientFactory):

    protocol = CurrencyProtocol


def main():
    from twisted.internet import reactor
    factory = CurrencyClientFactory()
    reactor.connectTCP(SERVER_HOST, SERVER_PORT, factory)
    reactor.run()

if __name__ == '__main__':
    main()
