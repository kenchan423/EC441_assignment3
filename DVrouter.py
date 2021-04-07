####################################################
# DVrouter.py
# Name:
# BU ID:
#####################################################

import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads

import networkx as nx

class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        # Hints: initialize local state

        # format: destination : distance aka cost
        self.dis_vec = {}
        # format: destination : distance vector
        self.all_dis_vec = {}

        # format: addr: port
        self.neighbors = {}

        # format dstAddr:port
        self.fwd_table = {}

        # for debugging
        self.most_recent = ''
        pass

    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
            # Hints: this is a normal data packet
            # if the forwarding table contains packet.dstAddr
            #   send packet based on forwarding table, e.g., self.send(port, packet)
            
            # if destination in forwarding table
            if packet.dstAddr in self.fwd_table:
                # and if forwarding table has a port (router) for that destination
                if self.fwd_table[packet.dstAddr] != 0:
                    # send the pkt
                    self.send(self.fwd_table[packet.dstAddr], packet)
            pass
        else:
            # Hints: this is a routing packet generated by your routing protocol
            # if the received distance vector is different
            #   update the local copy of the distance vector
            #   update the distance vector of this router
            #   update the forwarding table
            #   broadcast the distance vector of this router to neighbors

            # de-json packet content
            recv_dis_vec = loads(packet.content)
            self.most_recent = recv_dis_vec

            # update local copy of distance vector
            # if there's an DV for that address ...
            if packet.srcAddr in self.all_dis_vec:
                # if the DV recieved and the current entry are different
                if not recv_dis_vec == self.all_dis_vec[packet.srcAddr]:
                    self.all_dis_vec[packet.srcAddr] = recv_dis_vec
            else:
                # otherwise, there is yet a DV for that address --> must add DV
                self.all_dis_vec[packet.srcAddr] = recv_dis_vec
            
            # add src's neighbors to forward table --> discovering new nodes
            # dont add myself (b/c first condition doesnt tick since not in my own fowarding table)
            # initalize address: port --> 0
            for address in recv_dis_vec:
                if not self.fwd_table.has_key(address) and address != self.addr:
                    self.fwd_table[address] = 0
                if not packet.srcAddr in self.fwd_table:
                    self.fwd_table[packet.srcAddr] = 0
            
            # re-calculate DV 
            self.bellmanFord(self, packet.dstAddr)
            
            # broadcast DV
            for dst in self.neighbors:
                if self.neighbors[dst] != port: 
                    self.send(self.neighbors[dst], packet)


    def handleNewLink(self, port, endpoint, cost):
        """TODO: handle new link"""
        # update the distance vector of this router
        # update the forwarding table
        # broadcast the distance vector of this router to neighbors

        # create new entry in own distance vector, neighbors, fowarding table
        self.dis_vec[endpoint] = cost
        self.neighbors[endpoint] = port
        self.fwd_table[endpoint] = port
        
        # fowarding to neighbors
        for dst in self.neighbors:
            pkt = Packet(kind=Packet.ROUTING, srcAddr=self.addr, dstAddr=dst)
            pkt.content= dumps([self.dis_vec])
            self.send(self.neighbors[dst], pkt)


    def handleRemoveLink(self, port):
        """TODO: handle removed link"""
        # update the distance vector of this router
        # update the forwarding table
        # broadcast the distance vector of this router to neighbors

        # update distance vector
        # which neighbor matches to that port
        for friend in self.neighbors:
            if self.neighbors[friend] == port:
                to_remove = friend
                break
        # remove that entry from neighbors & DV
        self.neighbors.pop(to_remove)
        self.dis_vec.pop(to_remove)
        self.all_dis_vec.pop(to_remove)
        
        # update forwarding table
        for dst in self.fwd_table:
            if self.fwd_table[dst] == port:
                self.fwd_table.pop(dst)
                # re-calculate the bellman ford without that port available
                self.bellmanFord(self, dst)
                break

        # forward to all neighbors
        for dst in self.neighbors:
            pkt = Packet(kind=Packet.ROUTING, srcAddr=self.addr, dstAddr=dst)
            pkt.content= dumps([self.dis_vec])
            self.send(self.neighbors[dst], pkt)


    def handleTime(self, timeMillisecs):
        """TODO: handle current time"""
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            # broadcast the distance vector of this router to neighbors
            # forward to all neighbors
            for dst in self.neighbors:
                pkt = Packet(kind=Packet.ROUTING, srcAddr=self.addr, dstAddr=dst)
                pkt.content= dumps([self.dis_vec])
                self.send(self.neighbors[dst], pkt)
                pass

    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return 'Own DV: ' + str(self.dis_vec) +\
            '\nNeighbors: ' + str(self.neighbors) +\
            '\nNum. of Neighbors: ' + str(len(self.neighbors)) +\
            '\nNum. of Routers: ' + str(len(self.all_dis_vec)) +\
            '\nForward Table: ' + str(self.fwd_table) +\
            '\nMost recent packet recvd: ' +str(self.most_recent)
        pass

    def bellmanFord(self, dst):
        # No clue if this works :'(

        # objective: find the lowest cost from current (self) --> destination
        # first, go through each neighbor & their DV's --> add cost of self to neighbor + cost of neighbor to destination

        lowest_cost = 0
        # go through each neighbor
        for friend in self.neighbors:
            # cost of self --> neighbor
            friend_cost = self.dis_vec[friend] 
            # cost of neighbor --> dst
            friend_dv = self.all_dis_vec[friend]
            fri_to_dst = friend_dv[dst]
            # total cost = self-->neighbor + neighbor-->dst
            current_cost = friend_cost + fri_to_dst 
            # re-writing lowest cost if the cost of going through current neighbor is less 
            if current_cost < lowest_cost:
                lowest_cost = current_cost
                cheapest_friend = friend
        # returning lowest cost into dis_vec
        self.dis_vec[dst] = lowest_cost
        # adding port for that dst --> based on cheapest_friend (lowest_cost)
        self.fwd_table[dst] = self.neighbors[cheapest_friend]

