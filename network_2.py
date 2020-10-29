import queue
import threading
from rprint import print
import json


# wrapper class for a queue of packets
class Interface:
    # @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)

    # get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None

    # put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


# Implements a network layer packet.
class NetworkPacket:
    # packet encoding lengths
    dst_S_length = 5
    prot_S_length = 1

    # @param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S

    # called when printing the object
    def __str__(self):
        return self.to_byte_S()

    # convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise ('%s: unknown prot_S option: %s' % (self, self.prot_S))
        byte_S += self.data_S
        return byte_S

    # extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0: NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length: NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise ('%s: unknown prot_S field: %s' % (self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length:]
        return self(dst, prot_S, data_S)


# Implements a network host for receiving and transmitting data
class Host:

    # @param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False  # for thread termination

    # called when printing the object
    def __str__(self):
        return self.addr

    # create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out')  # send packets always enqueued successfully

    # receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))

    # thread target for the host to keep receiving data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            # receive data arriving to the in interface
            self.udt_receive()
            # terminate
            if (self.stop):
                print(threading.currentThread().getName() + ': Ending')
                return


# Implements a multi-interface router
# noinspection SpellCheckingInspection
class Router:

    # @param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False  # for thread termination
        self.name = name
        # create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        # save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D  # {neighbor: {interface: cost}}
        self.rt_tbl_D = {}  # {destination: {from-router: cost}}

        self.neighboring_routers = [self.name]
        for neighbor in self.cost_D:
            if Router.is_router(neighbor):  # check to see if neighbor is a router
                self.neighboring_routers.append(neighbor)

        for destination in ["H1", "H2", "RA", "RB"]:
            for router in self.neighboring_routers:
                if destination not in self.rt_tbl_D:
                    self.rt_tbl_D.update({destination: {router: "-"}})
                else:
                    self.rt_tbl_D[destination].update({router: "-"})
                if router == self.name and destination in self.cost_D:
                    for interface, cost in self.cost_D[destination].items():
                        self.rt_tbl_D[destination][router] = cost

        self.rt_tbl_D[self.name][self.name] = 0

        print('%s: Initialized routing table' % self)
        self.print_routes()

    @staticmethod
    def is_router(neighbor):
        if neighbor[0] == "R":
            return True
        else:
            return False

    # Print routing table
    def print_routes(self):
        table = "╒══════╤══════╤══════╤══════╤══════╕\n│ "
        table += self.name
        table += "   │"
        for destination in ["H1", "H2", "RA", "RB"]:
            table += "   " + destination + " │"
        table += "\n╞══════╪══════╪══════╪══════╪══════╡\n"

        for router in self.neighboring_routers:
            table += "│ " + router + "   │"
            for destination in ["H1", "H2", "RA", "RB"]:
                table += "    "
                table += str(self.rt_tbl_D[destination][router])
                table += " │"
            table += "\n├──────┼──────┼──────┼──────┼──────┤\n"
        print(table)

    # called when printing the object
    def __str__(self):
        return self.name

    # look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            # get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            # if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p, i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))

    # forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        last_hop = False  # flag to determine whether this is the last hop before destination
        cost_to_dst = self.rt_tbl_D[p.dst][self.name]
        next_hop_out_intf = None

        # checks if we're at last hop before destination and if so sets appropriate out intf
        if p.dst in self.cost_D and cost_to_dst == self.rt_tbl_D[p.dst][self.name]:
            next_hop_out_intf = list(self.cost_D[p.dst])[0]
            last_hop = True

        # if it's not the last hop before the destination, it determines the out intf of the next hop to reach dst
        if not last_hop:
            for neighbor in self.cost_D:
                if neighbor not in self.rt_tbl_D[p.dst]:
                    continue
                if self.rt_tbl_D[p.dst][neighbor] + self.rt_tbl_D[neighbor][self.name] == cost_to_dst:
                    next_hop_out_intf = list(self.cost_D[neighbor])[0]

        if next_hop_out_intf is None:
            return  # something went wrong, there is no hop that matches routing table

        try:
            self.intf_L[next_hop_out_intf].put(p.to_byte_S(), 'out', True)
            print('%s: forwarding packet "%s" from interface %d to %d' % \
                  (self, p, i, next_hop_out_intf))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass

    # send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        to_send = {"from": self.name, "rt_tbl": self.rt_tbl_D}
        json_to_send = json.dumps(to_send)
        p = NetworkPacket(0, 'control', json_to_send)  # create a routing table update packet
        try:
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass

    # forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):

        print('%s: Received routing update %s from interface %d' % (self, p, i))

        update = False  # flag to check if there has been an update to current router's cost to destinations
        src_router = json.loads(p.data_S)["from"]  # src of router who sent updated routing table
        rcvd_rt_tbl = json.loads(p.data_S)["rt_tbl"]  # received routing table

        # iterates over every destination in received routing table
        for destination in rcvd_rt_tbl:

            # if there isn't a cost for that destination move onto next destination
            if rcvd_rt_tbl[destination][src_router] == "-":
                continue

            # update the destination costs for the src router in the routing table
            self.rt_tbl_D[destination][src_router] = rcvd_rt_tbl[destination][src_router]

            # calculate the cost to the destination taking into account the new received cost from src router
            rcvd_cost_to_dest = int(self.rt_tbl_D[src_router][self.name]) + int(rcvd_rt_tbl[destination][src_router])

            curr_cost_to_dest = float('inf')  # sets default current cost to infinity

            # updates current cost if there is an actual cost saved
            if destination in self.rt_tbl_D and self.rt_tbl_D[destination][self.name] != "-":
                curr_cost_to_dest = int(self.rt_tbl_D[destination][self.name])

            # calcualtes new cost to destination by taking the min value of the received cost to destination and the
            # current cost to destination
            new_cost_to_dest = min(curr_cost_to_dest, rcvd_cost_to_dest)

            # if the new cost is different, it updates the routing table and sets the update flag to True
            if new_cost_to_dest != curr_cost_to_dest:
                self.rt_tbl_D[destination][self.name] = new_cost_to_dest
                update = True

        # checks if there were any updates, if so it sends new routes to all neighbor routers
        if update:
            for neighbor in self.cost_D:
                if Router.is_router(neighbor):
                    out_intf = list(self.cost_D[neighbor])[0]
                    self.send_routes(out_intf)

    # thread target for the host to keep forwarding data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return
