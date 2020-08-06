import datetime
import pickle
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from enum import Enum
from collections import Counter
from scapy.utils import RawPcapReader
from scapy.layers.all import *

# TODO Future upgrades: the links provided give csv file with this matching, so it could be cool to create these dictionaries starting from there


class PktDirection(Enum):
    not_defined = 0
    outgoing = 1
    incoming = 2


# To add other protocol layer 2, look at this link: https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml
protocol_mapping_l2 = {
    'ARP': 0x0806,
    'IPv4': 0x0800,
    'IEEE 802.1X': 0x0888E,
}

# To add other protocol numbers (layer 3), look at this link: https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml
protocol_mapping_l3 = {
    'ICMP': 1,
    'TCP': 6,
    'UDP': 17,
    'IPv6': 41,
    'IPv6-ICMP': 58,
    'TTP': 84, # Transaction Transfer Protocol
    'MTP': 92, # Multicast Transport Protocol
    'SMP': 121, # Simple Message Protocol
}

def direction_view(direction):
    if direction == PktDirection.incoming:
        return "<--"
    elif direction == PktDirection.outgoing:
        return "-->"
    else:
        return "---"



def file_log_counter_writing(opened_file, counter_dict, separator=""):

    for (proto, direction) in counter_dict.keys():
        pkts = counter_dict.get((proto,direction))
        opened_file.write("{}{}Protocol: {}...{}\n".format(separator, direction_view(direction), proto, pkts))



def mac_address_fixer(mac_address):
    """The folders provided use to have only a single zero when multiple zero are present in the same part of the address
    e.g. 00:af:... 0:af
    Args:
        mac_address: mac address to be fixed
    """
    new_mac = ''
    if '0' in mac_address.split(':')[0] and len(mac_address.split(':')[0]) == 1:
       new_mac = '0'
    new_mac += mac_address.replace (':0:',':00:')
    return new_mac



def destination_contacted(file_name, src_address, plotting=False):
    """
    This method provides an overview about the destinations contacted by a devices with a specific ip address. 
    Particularly, the methods return the number of packets send to all the destions
    Args:
        file_name: pcap file
        src_address: ip address to analalyse
        plotting: plot the result obtained
    """
    counter = Counter()
    for (pkt_data, pkt_metadata,) in RawPcapReader(file_name):
        
        # Obtaining ether packet 
        ether_pkt = Ether(pkt_data)
        
        if 'type' not in ether_pkt.fields:
            # LLC frames will have 'len' instead of 'type'.
            # We disregard those
            continue
        
        if ether_pkt.type != protocol_mapping_l2.get('IPv4'):
            continue
        
        ip_pkt = ether_pkt[IP]
        
        if ip_pkt.src != src_address:
            continue

        counter[ip_pkt.dst] += 1
    
    if plotting:
        fig, ax = plt.subplots(figsize = (7, 4)) 
        ax.set_title('Contacted destinations by {}'.format(src_address))
        plt.ylabel('# Packets')
        plt.xlabel('Destination Address')
        values = sorted(list(counter.values()), reverse=True)
        
        plt.bar(counter.keys(), values)
        for index, value in enumerate(values):
            plt.text(index, value, str(value), size=12, ha='center')
        plt.show()
        
    else:
        print("Destination contacted by {}: {}".format(src_addresscounter))
    


def packet_rate_filtering_by_protocol(file_name, mac_address, window=None):
    """
    The method produces an output file containing the packet rates organised in layers (e.g. IPv4...1000)
    Args:
        file_name: pcap file_name
        mac_address: device to be analysed
        window: sliding window allows to select count the packets send or received in a certain time window(default None) (time is in secs)
    """
    # TODO Add feature that loops in an entire folder (all pcap files in a folder)
    # TODO Add diurnal and nocturnal window
    # TODO Add new interesting protocols

    print("Processing {} ...".format(file_name))
    
    output_file_name = mac_address + "_analysis.log"
    
    # Layers refer to TCP/IP stack (layer1: Host-to-network, layer2: Internet(Network), layer3: Transport, layer4: Application)
    protocols_packet_counter_layer_1 = Counter()
    protocols_packet_counter_layer_2 = Counter()
    protocols_packet_counter_layer_3 = Counter()
    
    general_counter = 0 # Timestamp guideline
    window_counter = 0 # Useful for logging purposes

    protocols_code_l3 = list(protocol_mapping_l3.values())
    protocols_code_l2 = list(protocol_mapping_l2.values())

    # useful for debug = checking that all the packets were counted
    # debug = 0

    # In case of window enabled, the relative_timestamp must be set to zero before looping on the files
    relative_timestamp = 0 

    # Open log file
    log_file = open(output_file_name,'w')
    

    # In such a case the log file is going to be organised per pcap file instead of window 
    if window is None:
        print("To be defined")
    

    for (pkt_data, pkt_metadata,) in RawPcapReader(file_name):

        general_counter += 1
        # If window is enabled we should get the time stamp and reset all the counter
        if not window is None:
            # Computing timestamp

            if general_counter == 1: # This is useful only for the first packet (Is there a clever way?)
                # Computing firsttimestamp
                first_timestamp = datetime.datetime.fromtimestamp(pkt_metadata.sec)
                first_timestamp = (first_timestamp + datetime.timedelta(microseconds=pkt_metadata.usec)).timestamp()
            
            last_timestamp = datetime.datetime.fromtimestamp(pkt_metadata.sec)
            last_timestamp = (last_timestamp + datetime.timedelta(microseconds=pkt_metadata.usec)).timestamp()
            relative_timestamp = last_timestamp - first_timestamp

            # print(relative_timestamp)

            if relative_timestamp >= window:
                
                log_file.write("-------------------:Window::{}:-------------------\n".format(window_counter))
                
                # Counters writing
                file_log_counter_writing(log_file, protocols_packet_counter_layer_1)
                file_log_counter_writing(log_file, protocols_packet_counter_layer_2)
                file_log_counter_writing(log_file, protocols_packet_counter_layer_3, separator="\t")

                window_counter += 1
                
                
                # debug += sum(list(protocols_packet_counter_layer_2.values()))
                
                # Reset counter
                protocols_packet_counter_layer_1.clear() # Deletes all the elements keys + values
                protocols_packet_counter_layer_2.clear()
                protocols_packet_counter_layer_3.clear()
                general_counter = 1

                # Computing another time the first_timestamp
                first_timestamp = datetime.datetime.fromtimestamp(pkt_metadata.sec)
                first_timestamp = (first_timestamp + datetime.timedelta(microseconds=pkt_metadata.usec)).timestamp()

                # Reset relative_timestamp
                relative_timestamp = 0
        
        # Obtaining ether packet
        ether_pkt = Ether(pkt_data)
        
        direction = PktDirection.not_defined
        if 'type' not in ether_pkt.fields:
            # LLC frames will have 'len' instead of 'type'.
            # We disregard those
            protocols_packet_counter_layer_1[('UNDEFINED-L1', direction)] += 1
            continue
        
        
        # Considering only outbound packets
        if ether_pkt.src != mac_address and ether_pkt.dst != mac_address:
            continue

        # Defining direction
        if ether_pkt.src == mac_address:
            direction = PktDirection.outgoing
        else:
            direction = PktDirection.incoming

        # In this method only IP packets are considered (interesting for our purposes)
        if ether_pkt.type != protocol_mapping_l2.get('IPv4'):
            
            # It is possible that the type value is not our mapping
            if ether_pkt.type in protocols_code_l2:
                protocols_packet_counter_layer_2[(list(protocol_mapping_l2.keys())[protocols_code_l2.index(ether_pkt.type)], direction)] += 1
            else:
                print("Unrecognized type l2: {}".format(ether_pkt.type))
                protocols_packet_counter_layer_2[('UNDEFINED-L2', direction)] += 1
            continue
        
        protocols_packet_counter_layer_2[('IPv4',direction)] += 1
        
        ip_pkt = ether_pkt[IP]
        
        if ip_pkt.proto == protocol_mapping_l3.get('TCP'):
            # print("Found tcp packet")
            protocols_packet_counter_layer_3 [('TCP',direction)] += 1
            tcp_pkt = ip_pkt[TCP]
            
            if 'S' in str(tcp_pkt.flags) and not 'A' in str(tcp_pkt.flags):
                # Useful to understand the normal SYN traffic (avoiding SYN flood attacks)
                protocols_packet_counter_layer_3[("TCP-SYN-REQ-TO-" + ip_pkt.dst,direction)] +=1

        elif ip_pkt.proto in protocols_code_l3:
            protocols_packet_counter_layer_3 [(list(protocol_mapping_l3.keys())[protocols_code_l3.index(ip_pkt.proto)], direction)] += 1
        
        else:
            protocols_packet_counter_layer_3 ['UNDEFINED-L3'] += 1
        
    log_file.write("-------------------:Window::{}:-------------------\n".format(window_counter))
    
    # Counters writing
    file_log_counter_writing(log_file, protocols_packet_counter_layer_1)
    file_log_counter_writing(log_file, protocols_packet_counter_layer_2)
    file_log_counter_writing(log_file, protocols_packet_counter_layer_3, separator="\t")
    
    log_file.close()
    # debug += sum(list(protocols_packet_counter_layer_1.values()))
    # print(debug)

        
        
def packet_rate(file_name, mac_address, incoming=False, window=1, plotting=False):
    """
        This method computes the packet rate in output and in input to a particular device (same mac address)
        Args:
            file_name: pcap file to be processed,
            mac_address: mac address of the device,
            incoming: Allows to consider incoming packet as well,
            window: compute the packet rate for a particular time window (in sec) (default value 1, which means amount of packet per second),
            plotting: print and plot the results (otherwise print),
    """
    print("Processing {} ...".format(file_name))

    # TODO implement folder navigation (now only one file)\
    counter = 0

    # List containing how many packets have been sent in a time window
    interesting_packets = []
    relative_timestamp = 0
    total_counter = 0
    
    for (pkt_data, pkt_metadata,) in RawPcapReader(file_name):
        # Obtaining ether packet (Is it useful in such a case?)
        ether_pkt = Ether(pkt_data)
        
        # If incoming is enabled, only incoming packets (with dst address equal to our address) are considered
        if ether_pkt.src != mac_address and not incoming:
            continue
        elif ether_pkt.dst != mac_address and incoming:
            continue

        total_counter += 1
        if relative_timestamp >= window:
            interesting_packets.append(counter)
            counter = 1 # Otherwise the packet is going to be lost

            # So we need to recompute the timestamp of our first packet
            first_timestamp = datetime.datetime.fromtimestamp(pkt_metadata.sec)
            first_timestamp = (first_timestamp + datetime.timedelta(microseconds=pkt_metadata.usec)).timestamp()
            relative_timestamp = 0
        else:
            counter += 1
            if counter == 1: # This condition is valid ONLY ONCE in the entire analysis
                # Computing the first timestamp so that we can respect the window 
                # PAY ATTENTION: Depending on how the packets have been gathered, the timestamp computation may be different
                # In this case we have RawPcapReader object so pkt_metadata has sec and usec in two different fields
                first_timestamp = datetime.datetime.fromtimestamp(pkt_metadata.sec)
                first_timestamp = (first_timestamp + datetime.timedelta(microseconds=pkt_metadata.usec)).timestamp()

            last_timestamp = datetime.datetime.fromtimestamp(pkt_metadata.sec)
            last_timestamp = (last_timestamp + datetime.timedelta(microseconds=pkt_metadata.usec)).timestamp()
            relative_timestamp = last_timestamp - first_timestamp
        
        # Following line is for debugging purposes only
        # print("First time stamp: {}, last_timestamp:{}, relative_timestamp:{}".format(first_timestamp, last_timestamp, relative_timestamp))
    
    # Checking last packets
    if counter != 0:
        interesting_packets.append(counter)
    print(interesting_packets)
    print("Total incoming({}) packets {}".format(incoming, total_counter))
    print("List sum: {}".format(sum(interesting_packets)))
    print("List lenght: {}".format(len(interesting_packets)))
    print("Last counter: {}".format(counter))

    if plotting:
        fig, ax = plt.subplots(figsize = (7, 4)) 
        ax.set_title('Packet rate ({}) in a window of {} secs'.format(mac_address, window))
        plt.ylabel('# Packets')
        plt.xlabel('Time')
        values = list(range(0, len(interesting_packets)))
        
        plt.plot(values, interesting_packets)
        plt.show()


# print("Calling the method..")
# file_name = "/Users/angeloferaudo/Desktop/Research activities/Internship July-September/IoT Data/0:26:29:0:77:ce/unctrl/2019-08-08_11.01.14_192.168.20.165.pcap"
# # packet_rate(file_name, mac_address="00:26:29:00:77:ce", incoming=False, window=180, plotting=True)
# # destination_contacted(file_name,'192.168.20.254', plotting=True)
# packet_rate_filtering_by_protocol(file_name, mac_address="00:26:29:00:77:ce", window=180)