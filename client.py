from twisted.internet import task
from twisted.internet.protocol import Protocol, ClientFactory


SERVER_HOST = "localhost"
SERVER_PORT = 8000
CURRENCY = "USD/UAH"  # add currency pair you want to track, for example: "USD/UAH"
INTERVAL = 5  # add interval in seconds for obtaining currency pair rate

class CurrencyProtocol(Protocol):

    def connectionMade(self):
        print "Connection made"
        self.startLoop()

    def dataReceived(self, data):
        print "data received"
        print data

    def connectionLost(self, reason):
        print "connection lost", reason

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

if __name__ == "__main__":
    main()
