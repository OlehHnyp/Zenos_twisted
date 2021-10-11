from twisted.internet.protocol import ServerFactory, Protocol


PORT = 8000
HOST = 'localhost'

class CurrencyProtocol(Protocol):

    def connectionMade(self):
        print 'connection made'
        self.transport.write('Hello from server')
        self.transport.loseConnection()

    def connectionLost(self, reason):
        print 'connection lost', reason


class CurrencyServerFactory(ServerFactory):

    protocol = CurrencyProtocol



def main():
    factory = CurrencyServerFactory()
    from twisted.internet import reactor
    reactor.listenTCP(port=PORT, interface=HOST, factory=factory)
    reactor.run()

if __name__ == '__main__':
    main()
