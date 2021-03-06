import dns
import os
import socket
import struct
import threading
import clientsubnetoption
from recursortests import RecursorTest
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor

emptyECSText = 'No ECS received'
nameECS = 'ecs-echo.example.'

class ECSTest(RecursorTest):

    @classmethod
    def startResponders(cls):
        print("Launching responders..")

        address = cls._PREFIX + '.21'
        port = 53

        if not reactor.running:
            reactor.listenUDP(port, UDPECSResponder(), interface=address)

            cls._UDPResponder = threading.Thread(name='UDP ECS Responder', target=reactor.run, args=(False,))
            cls._UDPResponder.setDaemon(True)
            cls._UDPResponder.start()

    @classmethod
    def tearDownResponders(cls):
        reactor.stop()

    @classmethod
    def setUpClass(cls):
        cls.setUpSockets()

        cls.startResponders()

        confdir = os.path.join('configs', cls._confdir)
        cls.createConfigDir(confdir)

        cls.generateRecursorConfig(confdir)
        cls.startRecursor(confdir, cls._recursorPort)

        print("Launching tests..")

    @classmethod
    def tearDownClass(cls):
        cls.tearDownRecursor()

class testNoECS(ECSTest):
    _confdir = 'NoECS'

    _config_template = """edns-subnet-whitelist=
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', emptyECSText)

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', emptyECSText)

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testIncomingNoECS(ECSTest):
    _confdir = 'IncomingNoECS'

    _config_template = """edns-subnet-whitelist=
use-incoming-edns-subnet=yes
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', emptyECSText)

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', emptyECSText)

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testECSByName(ECSTest):
    _confdir = 'ECSByName'

    _config_template = """edns-subnet-whitelist=ecs-echo.example.
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/24')

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/24')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testECSByNameLarger(ECSTest):
    _confdir = 'ECSByNameLarger'

    _config_template = """edns-subnet-whitelist=ecs-echo.example.
ecs-ipv4-bits=32
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.1/32')

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.1/32')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testECSByNameSmaller(ECSTest):
    _confdir = 'ECSByNameLarger'

    _config_template = """edns-subnet-whitelist=ecs-echo.example.
ecs-ipv4-bits=16
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/16')

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/16')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testIncomingECSByName(ECSTest):
    _confdir = 'ECSIncomingByName'

    _config_template = """edns-subnet-whitelist=ecs-echo.example.
use-incoming-edns-subnet=yes
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '192.0.2.0/24')

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/24')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testIncomingECSByNameLarger(ECSTest):
    _confdir = 'ECSIncomingByNameLarger'

    _config_template = """edns-subnet-whitelist=ecs-echo.example.
use-incoming-edns-subnet=yes
ecs-ipv4-bits=32
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '192.0.2.1/32')

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.1/32')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testIncomingECSByNameSmaller(ECSTest):
    _confdir = 'ECSIncomingByNameSmaller'

    _config_template = """edns-subnet-whitelist=ecs-echo.example.
use-incoming-edns-subnet=yes
ecs-ipv4-bits=16
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '192.0.0.0/16')

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/16')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testIncomingECSByNameV6(ECSTest):
    _confdir = 'ECSIncomingByNameV6'

    _config_template = """edns-subnet-whitelist=ecs-echo.example.
use-incoming-edns-subnet=yes
ecs-ipv6-bits=128
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '2001:db8::1/128')

        ecso = clientsubnetoption.ClientSubnetOption('2001:db8::1', 128)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/24')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testECSNameMismatch(ECSTest):
    _confdir = 'ECSNameMismatch'

    _config_template = """edns-subnet-whitelist=not-the-right-name.example.
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', emptyECSText)

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', emptyECSText)

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testECSByIP(ECSTest):
    _confdir = 'ECSByIP'

    _config_template = """edns-subnet-whitelist=%s.21
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'], os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/24')

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/24')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testIncomingECSByIP(ECSTest):
    _confdir = 'ECSIncomingByIP'

    _config_template = """edns-subnet-whitelist=%s.21
use-incoming-edns-subnet=yes
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'], os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '192.0.2.0/24')

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', '127.0.0.0/24')

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class testECSIPMismatch(ECSTest):
    _confdir = 'ECSIPMismatch'

    _config_template = """edns-subnet-whitelist=192.0.2.1
forward-zones=ecs-echo.example=%s.21
    """ % (os.environ['PREFIX'])

    def testSendECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', emptyECSText)

        ecso = clientsubnetoption.ClientSubnetOption('192.0.2.1', 32)
        query = dns.message.make_query(nameECS, 'TXT', 'IN', use_edns=True, options=[ecso], payload=512)
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

    def testNoECS(self):
        expected = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', emptyECSText)

        query = dns.message.make_query(nameECS, 'TXT')
        res = self.sendUDPQuery(query)

        self.assertRcodeEqual(res, dns.rcode.NOERROR)
        self.assertRRsetInAnswer(res, expected)

class UDPECSResponder(DatagramProtocol):
    @staticmethod
    def ipToStr(option):
        if option.family == clientsubnetoption.FAMILY_IPV4:
            ip = socket.inet_ntop(socket.AF_INET, struct.pack('!L', option.ip))
        elif option.family == clientsubnetoption.FAMILY_IPV6:
            ip = socket.inet_ntop(socket.AF_INET6,
                                  struct.pack('!QQ',
                                              option.ip >> 64,
                                              option.ip & (2 ** 64 - 1)))
        return ip

    def datagramReceived(self, datagram, address):
        request = dns.message.from_wire(datagram)

        response = dns.message.make_response(request)

        if request.question[0].name == dns.name.from_text(nameECS) and request.question[0].rdtype == dns.rdatatype.TXT:
            text = emptyECSText
            for option in request.options:
                if option.otype == clientsubnetoption.ASSIGNED_OPTION_CODE and isinstance(option, clientsubnetoption.ClientSubnetOption):
                    text = self.ipToStr(option) + '/' + str(option.mask)

            answer = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'TXT', text)
            response.answer.append(answer)
        elif request.question[0].name == dns.name.from_text(nameECS) and request.question[0].rdtype == dns.rdatatype.NS:
            answer = dns.rrset.from_text(nameECS, 60, dns.rdataclass.IN, 'NS', 'ns1.ecs-echo.example.')
            response.answer.append(answer)
            additional = dns.rrset.from_text('ns1.ecs-echo.example.', 15, dns.rdataclass.IN, 'A', cls._PREFIX + '.21')
            response.additional.append(additional)

        self.transport.write(response.to_wire(), address)
