# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import re
from collections import defaultdict

import paramiko
from django.conf import settings

from ralph.util import plugin


logger = logging.getLogger(__name__)


def UnknowDataFormatError(Exception):
    """
    Raise this exception when data contains any different format like except
    """
    pass


def RemoteServerError(Exception):
    """
    Raise this exception when command executed on remote server trigger the
    error
    """
    pass


def get_ssh_client(address, login, password):
    """
    Create ssh client and connect them to give address by using given 
    credentials

    :param string address: Remote server address
    :param string login: User name to remote server
    :param string login: Password to remote server
    :returns object: ssh client with connection to remote server
    :rtype object:
    """
    logger.debug(
        'Getting client for {0} {1} ****'.format(
            address,
            login,
            password,
        )
    )
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(address, username=login, password=password)
    return ssh_client


def get_names_of_data_files(ssh_client, channel, date):
    """
    Generate list of file names from given channel and date. Execute
    simple ls on remote server in correct folder

    :param object ssh_client: Client connected to the remote server
    :param string channel: Channel name from which usages will be collects
    :param datetime date: Date for which usages will collects
    :returns list: list of file names
    :rtype list:
    """
    splited_date = str(date).split('-')
    stdin, stdout, stderr = ssh_client.exec_command(
        "ls /data/nfsen/profiles-data/live/{0}/{1}/{2}/{3}/".format(
            channel,
            splited_date[0],
            splited_date[1],
            splited_date[2],
        ),
    )
    if stderr.read():
        raise RemoteServerError(stderr.read())
    return sorted([row.strip('\n') for row in stdout.readlines()])


def execute_nfdump(ssh_client, channel, date, file_names, input_output):
    """
    Collects data by executing correct nfdump command on remote server

    :param object ssh_client: Client connected to the remote server
    :param string channel: Channel name from which usages will be collects
    :param datetime date: Date for which usages will collects
    :param list file_names: List with file names from remote server. This
    files contains trafic statistics.
    :param string input_output: Define direct of trafic (srcip or dstip)
    :returns list: list of rows from stdout from remote server
    :rtype list:
    """
    splited_date = str(date).split('-')
    nfdump_str = "nfdump -M /data/nfsen/profiles-data/live/{0} "\
        " -T  -R {1}/{2}/{3}/{4}:{1}/{2}/{3}/{5} -a  -A"\
        " {6} -o \"fmt:%sa | %da | %byt\"".format(
            channel,
            splited_date[0],
            splited_date[1],
            splited_date[2],
            file_names[0],
            file_names[-1],
            input_output,
        )
    stdin, stdout, stderr = ssh_client.exec_command(nfdump_str)
    if stderr.read():
        raise RemoteServerError(stderr.read())
    return stdout.readlines()[1:-4]


def extract_ip_and_bytes(row, input_output):
    """
    Extract/process ip address and usage in bytes from string. String is taken
    from executing nfdump commend on remote server and looks like:

    'scrip_ip_address | dstip_ip_address | usage_in_bytes'

    :param string row: Single row gain from remote server by execute nfdump
    commands
    :param string input_output: Define which address will be take
    :returns tuple: Pair ip_address with usage in bytes or None
    :rtype tuple:
    """
    def unification(bytes_string):
        bytes_list = bytes_string.split(' ')
        if len(bytes_list) == 1:
            return int(bytes_list[0])
        elif bytes_list[1] == 'M':
            return int(float(bytes_list[0]) * 1048576)
        elif bytes_list[1] == 'G':
            return int(float(bytes_list[0]) * 1073741824)
        else:
            raise UnknowDataFormatError(
                'Data cannot be unificated. Unknow field format'\
                ' \'{0} {1}\''.format(
                    bytes_list[0],
                    bytes_list[1],
                )
            )

    splited_row = [cell.replace('\x01', '').strip() for cell in row.split('|')]
    ip_address = splited_row[0]
    if input_output == 'dstip':
        ip_address = splited_row[1]

    for class_address in settings.NFSEN_CLASS_ADDRESS:
        if re.search(class_address, ip_address):
            return (ip_address, unification(splited_row[2]))


def get_network_usage(ssh_client, channel, date, file_names, input_output):
    """
    Collect usages for given channel, date and input/output. Used by
    get_network_usages method. Returned data struct looks like:

    Returned_data = {
        'ip_address': 'usage_in_bytes',
        ...
    }

    :param object ssh_client: Client connected to the remote server
    :param string channel: Channel name from which usages will be collects
    :param datetime date: Date for which usages will collects
    :param list file_names: List with file names from remote server. This
    files contains trafic statistics.
    :param string input_output: Define direct of trafic (srcip or dstip)
    :returns dict: list of ips with usages from given date
    :rtype dict:
    """
    ip_and_bytes = defaultdict(int)
    for row in execute_nfdump(ssh_client, channel, date, file_names, input_output):
        ip_and_byte = extract_ip_and_bytes(row, input_output)
        if ip_and_byte:
            ip_and_bytes[ip_and_byte[0]] = ip_and_byte[1]
    return ip_and_bytes


def get_network_usages(date):
    """
    Based on settings, collect data from remote server. Returned data struct
    looks like:

    Returned_data = {
        'ip_address': 'usage_in_bytes',
        ...
    }

    :param datetime date: Date for which usages will collects
    :returns dict: list of ips with usages from given date
    :rtype dict:
    """
    logger.debug('Getting network usages per IP')
    network_usages = defaultdict(int)
    for address, credentials in settings.SSH_NFSEN_CREDENTIALS.iteritems():
        ssh_client = get_ssh_client(address, **credentials)
        for channel in settings.NFSEN_CHANNELS:
            for input_output in ['srcip', 'dstip']:
                logging.debug("Serwer:{0} Channel:{1} I/O:{2}".format(
                    address, channel, input_output))
                for ip, value in get_network_usage(
                        ssh_client,
                        channel,
                        date,
                        get_names_of_data_files(ssh_client, channel, date),
                        input_output,
                    ).iteritems():
                    network_usages[ip] += value
    return network_usages


@plugin.register(chain='pricing', requires=['ventures'])
def network(**kwargs):
    """
    Getting network usage per venture is included in the two steppes.
    First of them is collect usages per ip and the second one is match
    ip with venture

    :param datetime today: Date for which usages will collects
    :returns tuple: Status, message and kwargs
    :rtype tuple:
    """
    if (not hasattr(settings, 'SSH_NFSEN_CREDENTIALS')
            or not settings.SSH_NFSEN_CREDENTIALS):
        return False, "Not configured credentials", kwargs

    if (not hasattr(settings, 'NFSEN_CHANNELS')
            or not settings.NFSEN_CHANNELS):
        return False, "Not configured channels", kwargs

    if (not hasattr(settings, 'NFSEN_CLASS_ADDRESS')
            or not settings.NFSEN_CLASS_ADDRESS):
        return False, "Not configured class address", kwargs

    date = kwargs['today']

    network_usages = get_network_usages(date)

    return True, "Status: ", kwargs
