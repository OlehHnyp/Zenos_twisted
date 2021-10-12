import sys
import os
import json
import csv

from twisted.internet import task
from twisted.internet.protocol import Protocol, ClientFactory


SERVER_HOST = "localhost"
SERVER_PORT = 8000
INTERVAL = 5  # add interval in seconds for obtaining currency pair rate

class CurrencyProtocol(Protocol):

    def connectionMade(self):
        print "Connection made"
        self.startLoop()

    def dataReceived(self, data):
        self.factory.writeIntoFile(data)

    def connectionLost(self, reason):
        print "connection lost", reason

    def startLoop(self):
        self._sender = task.LoopingCall(self.sendRequest)
        self._sender.start(interval=INTERVAL)

    def sendRequest(self):
        self.transport.write(self.factory.currency)


class CurrencyClientFactory(ClientFactory):

    protocol = CurrencyProtocol

    def __init__(self, currency):
        self.currency = currency
        self.file = "_".join(currency.split("/")) + ".csv"

    def _fileEmptyOrNotExist(self):
        return not os.path.isfile(self.file) or os.path.getsize(self.file) == 0

    def writeIntoFile(self, data):
        data = json.loads(data)
        with open(self.file, "a") as f:
            fieldnames = [
                'result',
                'base_code',
                'target_code',
                'conversion_rate',
                'time_last_update_utc',
                'time_last_update_unix',
                'time_next_update_utc',
                'time_next_update_unix'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if self._fileEmptyOrNotExist():
                writer.writeheader()
            writer.writerow(data)
            print "writing... ", self.currency


def main():
    from twisted.internet import reactor
    for currency in sys.argv[1:]:
        factory = CurrencyClientFactory(currency)
        reactor.connectTCP(SERVER_HOST, SERVER_PORT, factory)
    reactor.run()

if __name__ == "__main__":
    main()
